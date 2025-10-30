let actor = msg.globals.actor ? msg.globals.actor : "shift.jedillama.social";
let limit = msg.globals.limit ? msg.globals.limit : 1;

let post_url = `https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed?filter=posts_no_replies&actor=${actor}&limit=${limit}`

msg.url = post_url;

return msg;
