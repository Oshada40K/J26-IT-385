# CareerNova Google sign-in

Google is an additional sign-in method. Existing FastAPI email/password login and
all research APIs are preserved. The frontend creates a Supabase client from
`VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`; it uses PKCE and redirects to
`window.location.origin + '/auth/callback'`. The callback exchanges the code once,
including under React StrictMode. Supabase persists and refreshes the Google
session, while the dashboard guard accepts either account provider. The header
shows the user's name, email and picture. Logout clears the active provider's
session and the current CV credential; it does not restore an old password cookie.

## Environment

Install with `npm install` using Node.js 22 or newer. The supplied project URL and
public anon key are in the ignored `frontend/.env.local`. Source files contain no
credentials. `frontend/.env.example` lists the variable names.

In Vercel, set these for Production (and Preview if you need preview deployments):

| Variable | Value |
| --- | --- |
| `VITE_SUPABASE_URL` | `https://tyhecamapwyepdqnzlyn.supabase.co` |
| `VITE_SUPABASE_ANON_KEY` | The supplied public **anon** key, exactly as stored in `.env.local` |

Keep your existing production `VITE_API_BASE_URL` for the research backend. Vite
embeds public variables at build time: restart the dev server or redeploy Vercel
after updating them. Never place Google client secrets, Supabase service-role
keys or other private secrets in `VITE_*` variables. The public anon key is
intentionally browser-visible. This change does not access Supabase database
tables or change backend authorization.

## Supabase and Google configuration

In Supabase Authentication → URL Configuration:

- Site URL: `https://j26-it-385.vercel.app`
- Allowed redirect: `http://localhost:5173/auth/callback`
- Allowed redirect: `https://j26-it-385.vercel.app/auth/callback`
- If developing on 127.0.0.1, also add `http://127.0.0.1:5173/auth/callback`.

In Supabase Authentication → Sign In / Providers → Google, enable Google and set
the Google OAuth client ID and secret. The project already reported Google enabled
when checked; its private client configuration and redirect allowlist cannot be
verified using the public anon key.

In Google Cloud, use a Web application OAuth client:

- Authorized JavaScript origins: `http://localhost:5173` and `https://j26-it-385.vercel.app`
- Authorized redirect URI: `https://tyhecamapwyepdqnzlyn.supabase.co/auth/v1/callback`
- If the consent app is in Testing mode, add your Google account as a test user.

The Google callback points to Supabase; the frontend callback points to your app.
Vercel's existing rewrite to `/index.html` already handles direct visits and
refreshes of `/auth/callback` and dashboard routes. No Vercel rewrite change is needed.

See [Supabase Google sign-in configuration](https://supabase.com/docs/guides/auth/social-login/auth-google)
and [PKCE flow](https://supabase.com/docs/guides/auth/sessions/pkce-flow).

## Test

1. Run `npm run dev` and open `http://localhost:5173/login`.
2. Click **Continue with Google**, choose a permitted Google account, and finish consent.
3. Confirm you return to Home and the header shows your name, email and photo.
4. Refresh, then open `/component03` directly; the session should remain active.
5. Log out and revisit a dashboard URL; it should redirect to `/login`.
6. Repeat at `https://j26-it-385.vercel.app/login` after deployment.

Automated checks:

```powershell
npm run build
python tests/google_auth_browser.py http://localhost:5173
```

The browser test uses Python Playwright with Chromium and mocks Supabase HTTP
responses. It exercises the actual SDK for PKCE, refresh, profile display,
logout and callback errors without signing in to a real Google account. A real
Google consent round-trip must be completed interactively after the settings above
are configured.
