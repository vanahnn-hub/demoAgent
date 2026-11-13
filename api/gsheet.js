// Serverless function trên Vercel: Proxy tải dữ liệu Google Sheets tránh lỗi CORS
export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  const { url } = req.query;
  if (!url) {
    return res.status(400).json({ ok: false, error: 'Thiếu tham số url Google Sheets' });
  }

  try {
    const match = url.match(/\/spreadsheets\/d\/([a-zA-Z0-9\-_]+)/);
    if (!match) {
      return res.status(400).json({ ok: false, error: 'Đường dẫn Google Sheets không đúng định dạng' });
    }

    const sheetId = match[1];
    const gidMatch = url.match(/[#&?]gid=([0-9]+)/);
    const gid = gidMatch ? gidMatch[1] : '0';
    const exportUrl = `https://docs.google.com/spreadsheets/d/${sheetId}/export?format=csv&gid=${gid}`;

    const response = await fetch(exportUrl, {
      redirect: 'follow',
      headers: {
        'User-Agent': 'Mozilla/5.0 (compatible; GiaHoaAgent/1.0)'
      }
    });

    if (!response.ok) {
      return res.status(400).json({
        ok: false,
        error: `Không thể đọc Google Sheet (HTTP ${response.status}). Vui lòng kiểm tra quyền chia sẻ "Bất kỳ ai có đường liên kết đều có thể xem".`
      });
    }

    const csvText = await response.text();
    return res.status(200).json({ ok: true, csv: csvText });
  } catch (error) {
    return res.status(500).json({ ok: false, error: error.message });
  }
}

