
if (msg.payload) {
  delete msg.payload._id;
  delete msg.payload.tracked_in;
}

return msg;
