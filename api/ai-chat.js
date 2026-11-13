// Serverless function trên Vercel: Gọi Gemini API cho Trợ lý AI
export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  const prompt = req.body?.prompt || req.query?.prompt || 'Xin chào';
  const apiKey = req.headers['authorization']?.replace(/^Bearer\s+/i, '') || 
                 req.query?.apiKey || 
                 process.env.GEMINI_API_KEY || 
                 'AQ.Ab8RN6KNYAyjFtmst0jZBg4fx32YRNZLnfu3U1VKee32O7GRVw';

  try {
    const endpoint = `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${apiKey}`;
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contents: [{ parts: [{ text: prompt }] }],
        generationConfig: { temperature: 0.4, maxOutputTokens: 1024 }
      })
    });

    const data = await response.json();
    if (!response.ok) {
      return res.status(response.status).json({
        ok: false,
        error: data.error?.message || 'Lỗi khi gọi Gemini API'
      });
    }

    const reply = data.candidates?.[0]?.content?.parts?.[0]?.text || 'Không có phản hồi từ mô hình.';
    return res.status(200).json({ ok: true, reply });
  } catch (error) {
    return res.status(500).json({ ok: false, error: error.message });
  }
}

