// Netlify Function: neuestes YouTube-Video vom Kanal (RSS, keine Auth/kein API-Key).
// Umgeht das CORS-Problem eines direkten Browser-Fetch, indem der Feed serverseitig
// geholt wird. Antwort wird 1h gecacht (Card aktualisiert sich binnen ~1h nach Upload).
const CHANNEL_ID = "UCPgs2w8LKY9-lzu-z2BLAtw"; // Stefan_Rennrad_Chemnitz
const FEED = `https://www.youtube.com/feeds/videos.xml?channel_id=${CHANNEL_ID}`;

const CORS = { "Access-Control-Allow-Origin": "*" };

function decodeEntities(s) {
  return s
    .replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"').replace(/&#39;/g, "'")
    .replace(/&#(\d+);/g, (_, n) => String.fromCharCode(+n));
}

exports.handler = async () => {
  try {
    const resp = await fetch(FEED, { headers: { "User-Agent": "bockwurst-events/1.0" } });
    if (!resp.ok) {
      return { statusCode: 502, headers: CORS, body: JSON.stringify({ error: `feed ${resp.status}` }) };
    }
    const xml = await resp.text();

    // Das erste <entry> ist das neueste Video.
    const entry = xml.split("<entry>")[1] || "";
    const id = (entry.match(/<yt:videoId>([^<]+)<\/yt:videoId>/) || [])[1] || "";
    const titleRaw = (entry.match(/<title>([\s\S]*?)<\/title>/) || [])[1] || "";
    const title = decodeEntities(titleRaw.trim());

    if (!id) {
      return { statusCode: 502, headers: CORS, body: JSON.stringify({ error: "kein Video im Feed" }) };
    }

    return {
      statusCode: 200,
      headers: { "Content-Type": "application/json", "Cache-Control": "public, max-age=3600", ...CORS },
      body: JSON.stringify({
        id,
        title,
        url: `https://www.youtube.com/watch?v=${id}`,
        thumb: `https://i.ytimg.com/vi/${id}/hqdefault.jpg`,
      }),
    };
  } catch (e) {
    return { statusCode: 500, headers: CORS, body: JSON.stringify({ error: String(e) }) };
  }
};
