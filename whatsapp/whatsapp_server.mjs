// whatsapp_server.mjs
import express from 'express';
import makeWASocket, { useMultiFileAuthState, DisconnectReason } from '@whiskeysockets/baileys';
import qrcode from 'qrcode-terminal';

const PORT = 3001;
const API_KEY = process.env.WA_API_KEY

async function startServer() {
  const { state, saveCreds } = await useMultiFileAuthState('./auth_info');

  // create socket
  const sock = makeWASocket({
    auth: state,
    // optional: browser identification
    browser: ['Windows', 'Chrome', '1.0']
  });

  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('connection.update', (update) => {
    const { connection, qr } = update;
    if (qr) {
      console.log('📱 Scan this QR (one-time):');
      qrcode.generate(qr, { small: true });
    }
    if (connection === 'open') {
      console.log('✅ WhatsApp connected');
    }
    if (connection === 'close') {
      const reason = update.lastDisconnect?.error?.output?.statusCode;
      console.log('🔌 connection closed, reason:', reason);
      // do NOT auto-exit here; let process be restarted externally (pm2/systemd) if needed
    }
  });

  const app = express();
  app.use(express.json({ limit: '1mb' }));

  // simple auth middleware
  app.use((req, res, next) => {
    const key = req.headers['x-api-key'];
    if (!key || key !== API_KEY) return res.status(401).json({ ok: false, error: 'unauthorized' });
    next();
  });

  // health
  app.get('/health', (req, res) => res.json({ ok: true }));

  // send endpoint
  app.post('/send', async (req, res) => {
    const { number, message } = req.body;
    if (!number || !message) return res.status(400).json({ ok: false, error: 'number & message required' });

    const jid = number + '@s.whatsapp.net';

    try {
      // ensure socket is connected
      // If not connected, respond with 503 and a meaningful message
      // (you can add a check: sock.user exists)
      if (!sock?.user) {
        return res.status(503).json({ ok: false, error: 'WhastApp not connected' });
      }

      await sock.sendMessage(jid, { text: message });
      return res.json({ ok: true });
    } catch (err) {
      console.error('send error', err);
      // return error text (short)
      return res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.listen(PORT, () => console.log(`WhatsApp server listening on http://127.0.0.1:${PORT}`));
}

startServer().catch(e => {
  console.error('FATAL:', e);
  process.exit(1);
});
