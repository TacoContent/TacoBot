msg.collection = "shift_codes";

if (!msg.globals.guild_id) {
  msg.payload = "Missing Guild ID";
  throw "Missing Guild ID";
}

msg.sort = {
  "created_at": -1
};

msg.payload = {
  "tracked_in": {
    "$not": {
      "$elemMatch": {
        "guild_id": msg.globals.guild_id.toString()
      }
    }
  }
};

if (msg.globals.limit) {
  msg.limit = msg.globals.limit;
}

if (msg.globals.skip) {
  msg.skip = msg.globals.skip;
}

if (msg.globals.sort) {
  msg.sort = msg.globals.sort;
}

return msg;
