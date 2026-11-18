PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS accounts (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL DEFAULT '', company TEXT NOT NULL DEFAULT '',
 goals TEXT NOT NULL DEFAULT '[]', profile_ready INTEGER NOT NULL DEFAULT 0,
 created INTEGER NOT NULL, trial_until INTEGER NOT NULL, paid_until INTEGER NOT NULL DEFAULT 0,
 login_method TEXT NOT NULL DEFAULT 'guest', notification_seen INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS holds (
 account_id INTEGER PRIMARY KEY REFERENCES accounts(id) ON DELETE CASCADE, since INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS identities (
 provider TEXT NOT NULL, subject TEXT NOT NULL, account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
 PRIMARY KEY(provider,subject)
);
CREATE TABLE IF NOT EXISTS consents (
 account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
 version TEXT NOT NULL, accepted INTEGER NOT NULL, method TEXT NOT NULL, PRIMARY KEY(account_id,version)
);
CREATE TABLE IF NOT EXISTS sessions (
 token TEXT PRIMARY KEY, account_id INTEGER REFERENCES accounts(id) ON DELETE CASCADE, expires INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_expiry ON sessions(expires);
CREATE TABLE IF NOT EXISTS challenges (
 id TEXT PRIMARY KEY, session_token TEXT NOT NULL REFERENCES sessions(token) ON DELETE CASCADE,
 provider TEXT NOT NULL, subject TEXT NOT NULL DEFAULT '', proof TEXT NOT NULL, nonce TEXT NOT NULL DEFAULT '',
 expires INTEGER NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, consent_version TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS challenge_session ON challenges(session_token,provider);
CREATE TABLE IF NOT EXISTS rate_limits (key TEXT PRIMARY KEY, hits INTEGER NOT NULL, resets INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS clients (
 id INTEGER PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
 name TEXT NOT NULL, email TEXT NOT NULL DEFAULT '', company TEXT NOT NULL DEFAULT '', created INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS clients_owner ON clients(account_id,created DESC,id DESC);
CREATE TABLE IF NOT EXISTS tasks (
 id INTEGER PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
 title TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'Работа', done INTEGER NOT NULL DEFAULT 0 CHECK(done IN (0,1)),
 template TEXT, created INTEGER NOT NULL, UNIQUE(account_id,template)
);
CREATE INDEX IF NOT EXISTS tasks_owner ON tasks(account_id,done,id DESC);
CREATE TABLE IF NOT EXISTS events (
 id INTEGER PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
 kind TEXT NOT NULL, title TEXT NOT NULL, detail TEXT NOT NULL, created INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS events_owner ON events(account_id,id DESC);
CREATE TABLE IF NOT EXISTS payments (
 id TEXT PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
 amount INTEGER NOT NULL CHECK(amount>0), state TEXT NOT NULL CHECK(state IN ('pending','succeeded','canceled')),
 external_id TEXT UNIQUE, url TEXT NOT NULL DEFAULT '', created INTEGER NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS payments_open ON payments(account_id) WHERE state='pending';
CREATE INDEX IF NOT EXISTS payments_owner ON payments(account_id, created DESC);
PRAGMA user_version=1;
