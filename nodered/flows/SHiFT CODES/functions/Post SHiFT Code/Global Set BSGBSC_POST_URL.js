if (!msg.globals.post_url) {
  msg.globals.post_url = "http://lb.bit13.local:8931/webhook/shift";
}

global.set("BSGBSC_POST_URL", msg.globals.post_url);
return msg;
