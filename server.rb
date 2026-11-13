#!/usr/bin/env ruby
# encoding: utf-8
# AI301 - ĐỀ DỰ ÁN 08: LOCALHOST SERVER CHO AI AGENT CÔNG TY GIA HÒA
# Chạy tại: http://localhost:8080

require 'webrick'
require 'json'
require 'net/http'
require 'uri'

PORT = (ARGV[0] || 8080).to_i
ROOT_DIR = File.expand_path(File.dirname(__FILE__))
DEFAULT_API_KEY = 'AQ.Ab8RN6KNYAyjFtmst0jZBg4fx32YRNZLnfu3U1VKee32O7GRVw'

server = WEBrick::HTTPServer.new(
  Port: PORT,
  BindAddress: '127.0.0.1',
  DocumentRoot: ROOT_DIR,
  AccessLog: [[File.open(File::NULL, 'w'), WEBrick::AccessLog::COMMON_LOG_FORMAT]],
  Logger: WEBrick::Log.new($stdout, WEBrick::Log::INFO)
)

# Endpoint proxy tải Google Sheets CSV phía Server để tránh lỗi CORS trình duyệt
server.mount_proc '/api/gsheet' do |req, res|
  res['Content-Type'] = 'application/json; charset=utf-8'
  res['Access-Control-Allow-Origin'] = '*'
  begin
    sheet_url = req.query['url'].to_s.strip
    match = sheet_url.match(%r{/spreadsheets/d/([a-zA-Z0-9\-_]+)})
    unless match
      res.status = 400
      res.body = JSON.generate({ ok: false, error: 'Link Google Sheets không hợp lệ' })
      next
    end
    sheet_id = match[1]
    gid_match = sheet_url.match(/[#&?]gid=([0-9]+)/)
    gid = gid_match ? gid_match[1] : '0'
    export_url = "https://docs.google.com/spreadsheets/d/#{sheet_id}/export?format=csv&gid=#{gid}"

    uri = URI.parse(export_url)
    response = nil
    5.times do
      http = Net::HTTP.new(uri.host, uri.port)
      http.use_ssl = (uri.scheme == 'https')
      request = Net::HTTP::Get.new(uri.request_uri)
      response = http.request(request)
      if response.is_a?(Net::HTTPRedirection)
        uri = URI.parse(response['location'])
      else
        break
      end
    end

    if response && response.code.to_i == 200
      csv_text = response.body.force_encoding('UTF-8')
      res.body = JSON.generate({ ok: true, csv: csv_text })
    else
      res.status = 400
      res.body = JSON.generate({ ok: false, error: "Không tải được Google Sheet (HTTP #{response ? response.code : 'ERR'})" })
    end
  rescue => e
    res.status = 500
    res.body = JSON.generate({ ok: false, error: e.message })
  end
end

# Endpoint gọi Gemini / Vertex AI Express Mode API
server.mount_proc '/api/ai-chat' do |req, res|
  res['Content-Type'] = 'application/json; charset=utf-8'
  res['Access-Control-Allow-Origin'] = '*'
  res['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
  res['Access-Control-Allow-Headers'] = 'Content-Type'

  if req.request_method == 'OPTIONS'
    res.status = 200
    res.body = ''
    next
  end

  begin
    payload = JSON.parse(req.body.to_s)
    api_key = (payload['apiKey'] && !payload['apiKey'].strip.empty?) ? payload['apiKey'].strip : DEFAULT_API_KEY
    prompt_text = payload['prompt'].to_s
    system_instruction = payload['systemInstruction'].to_s

    models_to_try = ['gemini-2.5-flash', 'gemini-2.0-flash']
    last_err = nil
    reply_text = nil

    models_to_try.each do |model_name|
      endpoint = if api_key.start_with?('AQ.')
                   "https://aiplatform.googleapis.com/v1/publishers/google/models/#{model_name}:generateContent?key=#{URI.encode_www_form_component(api_key)}"
                 else
                   "https://generativelanguage.googleapis.com/v1beta/models/#{model_name}:generateContent?key=#{URI.encode_www_form_component(api_key)}"
                 end

      uri = URI.parse(endpoint)
      http = Net::HTTP.new(uri.host, uri.port)
      http.use_ssl = true
      http.read_timeout = 30

      body_obj = {
        contents: [
          {
            role: 'user',
            parts: [{ text: "#{system_instruction}\n\n---\nCÂU HỎI CỦA NGƯỜI DÙNG:\n#{prompt_text}" }]
          }
        ],
        generationConfig: {
          temperature: 0.3,
          maxOutputTokens: 1200
        }
      }

      request = Net::HTTP::Post.new(uri.request_uri, { 'Content-Type' => 'application/json' })
      request.body = JSON.generate(body_obj)
      response = http.request(request)

      if response.code.to_i == 200
        data = JSON.parse(response.body.force_encoding('UTF-8'))
        candidates = data['candidates'] || []
        if candidates.any? && candidates[0]['content'] && candidates[0]['content']['parts']
          reply_text = candidates[0]['content']['parts'].map { |p| p['text'].to_s }.join("\n")
          break if reply_text && !reply_text.empty?
        end
      else
        last_err = "HTTP #{response.code}: #{response.body}"
      end
    end

    if reply_text && !reply_text.empty?
      res.body = JSON.generate({ ok: true, reply: reply_text })
    else
      res.status = 502
      res.body = JSON.generate({ ok: false, error: last_err || 'Không nhận được phản hồi từ Gemini API' })
    end
  rescue => e
    res.status = 500
    res.body = JSON.generate({ ok: false, error: e.message })
  end
end

# Endpoint kiểm tra trạng thái Agent Server
server.mount_proc '/api/health' do |req, res|
  res['Content-Type'] = 'application/json; charset=utf-8'
  res.body = JSON.generate({
    status: 'running',
    project: 'AI301 - Đề Dự Án 08 - Công ty Gia Hòa',
    ai_key_configured: true,
    url: "http://localhost:#{PORT}"
  })
end

trap('INT') { server.shutdown }
trap('TERM') { server.shutdown }

puts "=================================================================="
puts "🚀 AI AGENT CÔNG TY GIA HÒA (ĐỀ DỰ ÁN 08) ĐANG CHẠY TẠI LOCALHOST"
puts "🔑 Đã tích hợp Vertex AI / Gemini API Key (AQ.Ab8RN6K...)"
puts "👉 Địa chỉ truy cập: http://localhost:#{PORT}"
puts "=================================================================="
$stdout.flush

server.start
