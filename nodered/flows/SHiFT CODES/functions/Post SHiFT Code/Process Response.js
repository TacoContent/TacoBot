if (msg.payload.error) {
  msg.payload = null;
  return msg;
}

if (msg.payload === '') {
  msg.payload = null;
  return msg;
}

return msg;
