// Netlify Function: Proxy für GitHub Issues API
// Token wird als Netlify Environment Variable gesetzt (nie im Code)
exports.handler = async (event) => {
  if (event.httpMethod !== "POST") {
    return { statusCode: 405, body: "Method not allowed" };
  }

  const token = process.env.GITHUB_ISSUES_TOKEN;
  if (!token) {
    return { statusCode: 500, body: JSON.stringify({ error: "Token not configured" }) };
  }

  let payload;
  try {
    payload = JSON.parse(event.body);
  } catch {
    return { statusCode: 400, body: JSON.stringify({ error: "Invalid JSON" }) };
  }

  const resp = await fetch(
    "https://api.github.com/repos/stefangriessmann/sport-events/issues",
    {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
        "Accept": "application/vnd.github+json",
      },
      body: JSON.stringify(payload),
    }
  );

  const data = await resp.json();
  return {
    statusCode: resp.status,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  };
};
