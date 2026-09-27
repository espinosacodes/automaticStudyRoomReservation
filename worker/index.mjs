const ORIGIN = 'https://reservation.getcuria.us'
const encoder = new TextEncoder()
const SESSION = '__Host-reservation'
const FLOW = '__Host-google-flow'
const secure = 'Path=/; HttpOnly; Secure; SameSite=Lax'
const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' } })
const encode = (bytes) => btoa(String.fromCharCode(...bytes)).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '')
const decode = (value) => Uint8Array.from(atob(value.replaceAll('-', '+').replaceAll('_', '/')), (c) => c.charCodeAt(0))
const random = () => encode(crypto.getRandomValues(new Uint8Array(32)))
const now = () => Math.floor(Date.now() / 1000)
const cookie = (request, name) => request.headers.get('cookie')?.split(';').map((v) => v.trim()).find((v) => v.startsWith(name + '='))?.slice(name.length + 1)
const allowed = (env, email) => (env.ALLOWED_EMAILS || '').split(',').map((v) => v.trim().toLowerCase()).includes(email?.toLowerCase())
async function key(env) {
  if (!env.SESSION_SECRET) throw new Error('Authentication not configured')
  return crypto.subtle.importKey('raw', encoder.encode(env.SESSION_SECRET), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign', 'verify'])
}
export async function sign(env, payload) {
  const data = encode(encoder.encode(JSON.stringify(payload)))
  return data + '.' + encode(new Uint8Array(await crypto.subtle.sign('HMAC', await key(env), encoder.encode(data))))
}
export async function verify(env, value) {
  try {
    const [data, signature, extra] = (value || '').split('.')
    if (extra || !await crypto.subtle.verify('HMAC', await key(env), decode(signature), encoder.encode(data))) return null
    const payload = JSON.parse(new TextDecoder().decode(decode(data)))
    return Number.isFinite(payload.exp) && payload.exp > now() ? payload : null
  } catch { return null }
}
function redirect(path, cookies = []) {
  const headers = new Headers({ location: ORIGIN + path, 'cache-control': 'no-store' })
  for (const value of cookies) headers.append('set-cookie', value)
  return new Response(null, { status: 302, headers })
}
async function member(request, env) {
  const session = await verify(env, cookie(request, SESSION))
  return session?.kind === 'session' && allowed(env, session.email) ? session : null
}
async function handler(request, env) {
  const url = new URL(request.url)
  const path = url.pathname
  if (path === '/auth/session') {
    const user = await member(request, env)
    return json({ user: user ? { email: user.email } : null, configured: Boolean(env.GOOGLE_CLIENT_ID && env.GOOGLE_CLIENT_SECRET && env.SESSION_SECRET) })
  }
  if (path === '/auth/logout') {
    if (request.method !== 'POST' || request.headers.get('origin') !== url.origin) return json({ error: 'Forbidden' }, 403)
    return new Response(null, { status: 204, headers: { 'set-cookie': `${SESSION}=; ${secure}; Max-Age=0`, 'cache-control': 'no-store' } })
  }
  if (path === '/auth/google') {
    if (url.origin !== ORIGIN) return redirect('/auth/google')
    if (!env.GOOGLE_CLIENT_ID || !env.GOOGLE_CLIENT_SECRET) return redirect('/?auth_error=configuration')
    const state = random()
    const verifier = random()
    const challenge = encode(new Uint8Array(await crypto.subtle.digest('SHA-256', encoder.encode(verifier))))
    const flow = await sign(env, { kind: 'flow', state, verifier, exp: now() + 600 })
    const target = new URL('https://accounts.google.com/o/oauth2/v2/auth')
    target.search = new URLSearchParams({ client_id: env.GOOGLE_CLIENT_ID, redirect_uri: ORIGIN + '/auth/callback', response_type: 'code', scope: 'openid email', state, code_challenge: challenge, code_challenge_method: 'S256', prompt: 'select_account' })
    return new Response(null, { status: 302, headers: { location: target.href, 'set-cookie': `${FLOW}=${flow}; ${secure}; Max-Age=600`, 'cache-control': 'no-store' } })
  }
  if (path === '/auth/callback') {
    const clear = `${FLOW}=; ${secure}; Max-Age=0`
    const flow = await verify(env, cookie(request, FLOW))
    if (url.origin !== ORIGIN || flow?.kind !== 'flow' || !url.searchParams.get('state') || flow.state !== url.searchParams.get('state') || !url.searchParams.get('code')) return redirect('/?auth_error=invalid', [clear])
    const tokenResponse = await fetch('https://oauth2.googleapis.com/token', { method: 'POST', body: new URLSearchParams({ code: url.searchParams.get('code'), client_id: env.GOOGLE_CLIENT_ID, client_secret: env.GOOGLE_CLIENT_SECRET, redirect_uri: ORIGIN + '/auth/callback', grant_type: 'authorization_code', code_verifier: flow.verifier }) })
    if (!tokenResponse.ok) return redirect('/?auth_error=invalid', [clear])
    const token = await tokenResponse.json()
    if (!token.access_token) return redirect('/?auth_error=invalid', [clear])
    const profileResponse = await fetch('https://openidconnect.googleapis.com/v1/userinfo', { headers: { Authorization: 'Bearer ' + token.access_token } })
    if (!profileResponse.ok) return redirect('/?auth_error=invalid', [clear])
    const profile = await profileResponse.json()
    if (profile.email_verified !== true || !profile.sub || !allowed(env, profile.email)) return redirect('/?auth_error=denied', [clear])
    const session = await sign(env, { kind: 'session', email: profile.email.toLowerCase(), sub: profile.sub, exp: now() + 43200 })
    return redirect('/', [clear, `${SESSION}=${session}; ${secure}; Max-Age=43200`])
  }
  // Only the empty application shell and hashed JS/CSS assets are public.
  const shell = path === '/' || path === '/index.html' || path === '/favicon.svg' || /^\/assets\/[\w-]+\.(js|css)$/.test(path)
  const machine = path === '/status.json' && env.STATUS_READ_TOKEN && request.headers.get('authorization') === `Bearer ${env.STATUS_READ_TOKEN}`
  if (!shell && !machine && !await member(request, env)) return json({ error: 'Sign in required' }, 401)
  const asset = await env.ASSETS.fetch(request)
  const response = new Response(asset.body, asset)
  response.headers.set('cache-control', shell && path.startsWith('/assets/') ? 'public, max-age=31536000, immutable' : 'private, no-store')
  response.headers.set('x-content-type-options', 'nosniff')
  response.headers.set('referrer-policy', 'same-origin')
  response.headers.set('x-frame-options', 'DENY')
  return response
}
export default { async fetch(request, env) {
  try { return await handler(request, env) } catch { return json({ error: 'Authentication temporarily unavailable' }, 503) }
} }
