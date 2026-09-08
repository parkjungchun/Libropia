// Cloudflare Worker: 텔레그램 "그만 받기"/"다시 받고싶어요" 버튼을 즉시 처리하는 웹훅
//
// 필요한 환경변수 (Cloudflare 대시보드 → Settings → Variables and Secrets 에 등록):
//   TELEGRAM_BOT_TOKEN : 텔레그램 봇 토큰
//   GITHUB_TOKEN       : GitHub Fine-grained 토큰 (Contents: Read and write 권한 필요)
//   GITHUB_REPO        : 예) "parkjungchun/Libropia"

export default {
  async fetch(request, env) {
    if (request.method !== "POST") {
      return new Response("OK");
    }

    let update;
    try {
      update = await request.json();
    } catch (e) {
      return new Response("OK");
    }

    const cb = update.callback_query;
    if (!cb) {
      return new Response("OK");
    }

    const chatId = cb.message.chat.id;
    const data = cb.data;

    if (data === "stop") {
      await tg(env, "answerCallbackQuery", {
        callback_query_id: cb.id,
        text: "알림을 중지했어요.",
      });
      await setPaused(env, true);
      await tg(env, "sendMessage", {
        chat_id: chatId,
        text: "알림을 중지했어요. 다시 받고 싶을 때 아래 버튼을 눌러주세요.",
        reply_markup: JSON.stringify({
          inline_keyboard: [[{ text: "▶️ 다시 받고싶어요", callback_data: "resume" }]],
        }),
      });
    } else if (data === "resume") {
      await tg(env, "answerCallbackQuery", {
        callback_query_id: cb.id,
        text: "알림을 다시 시작할게요.",
      });
      await setPaused(env, false);
      await tg(env, "sendMessage", {
        chat_id: chatId,
        text: "알림을 다시 시작할게요.",
      });
    }

    return new Response("OK");
  },
};

async function tg(env, method, body) {
  await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/${method}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

async function setPaused(env, paused) {
  const apiUrl = `https://api.github.com/repos/${env.GITHUB_REPO}/contents/state.json`;
  const headers = {
    Authorization: `Bearer ${env.GITHUB_TOKEN}`,
    "User-Agent": "seat-bot-worker",
    Accept: "application/vnd.github+json",
  };

  const getResp = await fetch(apiUrl, { headers });
  const current = await getResp.json();

  let state = { paused: false };
  try {
    state = JSON.parse(decodeURIComponent(escape(atob(current.content))));
  } catch (e) {
    // state.json이 없거나 읽기 실패하면 기본값 사용
  }
  state.paused = paused;

  const newContent = btoa(unescape(encodeURIComponent(JSON.stringify(state, null, 2))));

  await fetch(apiUrl, {
    method: "PUT",
    headers,
    body: JSON.stringify({
      message: paused ? "알림 중지 (웹훅)" : "알림 재개 (웹훅)",
      content: newContent,
      sha: current.sha,
    }),
  });
}
