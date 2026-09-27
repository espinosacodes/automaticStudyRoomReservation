import test from 'node:test'
import assert from 'node:assert/strict'
import worker, { sign } from './index.mjs'
const origin = 'https://reservation.getcuria.us'
const env = { SESSION_SECRET: 'test-only-secret', ALLOWED_EMAILS: 'member@example.com', GOOGLE_CLIENT_ID: 'test-client', GOOGLE_CLIENT_SECRET: 'test-secret', STATUS_READ_TOKEN: 'ci-secret', ASSETS: { fetch: async () => new Response('asset') } }
const request = (path, init) => new Request(origin + path, init)

test('private status and PDF routes require server authentication', async () => {
  for (const path of ['/status.json', '/bookings/receipt.pdf', '/other.json']) {
    assert.equal((await worker.fetch(request(path), env)).status, 401)
  }
  assert.equal((await worker.fetch(request('/'), env)).status, 200)
})
test('signed sessions are allowlisted, expire and cannot be forged', async () => {
  for (const [email, exp, suffix, expected] of [
    ['member@example.com', Date.now()/1000+60, '', 200],
    ['outsider@example.com', Date.now()/1000+60, '', 401],
    ['member@example.com', 0, '', 401],
    ['member@example.com', Date.now()/1000+60, 'tampered', 401],
  ]) {
    const value = await sign(env, { kind: 'session', email, exp })
    const response = await worker.fetch(request('/status.json', { headers: { cookie: '__Host-reservation=' + value + suffix } }), env)
    assert.equal(response.status, expected)
    assert.match(response.headers.get('cache-control'), /no-store/)
  }
})
test('CI read token does not grant access to PDF routes', async () => {
  const headers = { authorization: 'Bearer ci-secret' }
  assert.equal((await worker.fetch(request('/status.json', { headers }), env)).status, 200)
  assert.equal((await worker.fetch(request('/bookings/receipt.pdf', { headers }), env)).status, 401)
})
test('OAuth start uses PKCE and a secure state cookie', async () => {
  const response = await worker.fetch(request('/auth/google'), env)
  const target = new URL(response.headers.get('location'))
  assert.equal(target.hostname, 'accounts.google.com')
  assert.equal(target.searchParams.get('code_challenge_method'), 'S256')
  assert.match(response.headers.get('set-cookie'), /HttpOnly; Secure; SameSite=Lax/)
})
test('callback denies missing state, unverified emails, and nonmembers', async () => {
  assert.match((await worker.fetch(request('/auth/callback?code=x'), env)).headers.get('location'), /auth_error=invalid/)
  const original = globalThis.fetch
  try {
    for (const [email, verified, expected] of [['outsider@example.com', true, 'denied'], ['member@example.com', false, 'denied'], ['member@example.com', true, null]]) {
      globalThis.fetch = async (url) => new Response(JSON.stringify(String(url).includes('/token') ? { access_token: 'token' } : { sub: 'google-sub', email, email_verified: verified }), { headers: { 'content-type': 'application/json' } })
      const flow = await sign(env, { kind: 'flow', state: 'state', verifier: 'verifier', exp: Date.now()/1000+60 })
      const response = await worker.fetch(request('/auth/callback?state=state&code=code', { headers: { cookie: '__Host-google-flow=' + flow } }), env)
      assert.equal(response.headers.get('location'), origin + (expected ? '/?auth_error=' + expected : '/'))
      assert.equal(response.headers.get('set-cookie').includes('__Host-reservation='), !expected)
    }
  } finally { globalThis.fetch = original }
})
test('logout requires a same-origin POST', async () => {
  assert.equal((await worker.fetch(request('/auth/logout'), env)).status, 403)
  assert.equal((await worker.fetch(request('/auth/logout', { method: 'POST', headers: { origin } }), env)).status, 204)
})
