/***
 * Process GBSC Post
 ***/

const KNOWN_GAMES = [
  {
    "id": "bl0",
    "name": "Borderlands: The Pre-Sequel",
    "regex": /(?:Borderlands: The Pre-Sequel|BL:?TPS)/gi,
    "platforms": ["Steam", "Epic", "XBOX", "PSN", "Switch"]
  },
  {
    "id": "bl1goty",
    "name": "Borderlands: Game of the Year Edition",
    "regex": /(?:Borderlands(?:\: Game of the Year(?:\sEdition)?)?(?! 2| 3| 4|: The Pre-Sequel)|BL(?:[\:]?GOTY)?(?!\:?2|\:?3|\:?TPS))/gi,
    "platforms": ["Steam", "Epic", "XBOX", "PSN", "Switch"]
  },
  {
    "id": "bl2",
    "name": "Borderlands 2",
    "regex": /(?:Borderlands 2|BL[\:]?2)/gi,
    "platforms": ["Steam", "Epic", "XBOX", "PSN", "Switch"]
  },
  {
    "id": "bl3",
    "name": "Borderlands 3",
    "regex": /(?:Borderlands 3|BL[\:]?3)/gi,
    "platforms": ["Steam", "Epic", "XBOX", "PSN", "Switch"]
  },
  {
    "id": "bl4",
    "name": "Borderlands 4",
    "regex": /(?:Borderlands 4|BL[\:]?4)/gi,
    "platforms": ["Steam", "Epic", "XBOX", "PSN", "Switch"]
  },
  {
    "id": "ttw",
    "name": "Tiny Tina's Wonderlands",
    // Match both straight and curly apostrophes
    "regex": /(?:Tiny Tina['’]s Wonderlands|TTW[L]?)/gi,
    "platforms": ["Steam", "Epic", "XBOX", "PSN"]
  }
];

function toUnixTimestamp(dateStr) {
  if (!dateStr) return null;
  // Accepts YYYY-MM-DD only
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(dateStr.trim());
  if (!m) return null;
  return Math.floor(new Date(`${m[1]}-${m[2]}-${m[3]}T00:00:00Z`).getTime() / 1000);
}

function cleanGame(title) {
  for (let game of KNOWN_GAMES) {
    if (game.regex.test(title)) {
      return { id: game.id, name: game.name };
    }
  }
  return null;
}

function getPlatformsForGameId(gameId) {
  const game = KNOWN_GAMES.find(g => g.id === gameId);
  return game ? game.platforms : [];
}

function getAllPlatforms(games) {
  const platformSet = new Set();
  for (let game of games) {
    const platforms = getPlatformsForGameId(game.id);
    for (let p of platforms) {
      platformSet.add(p);
    }
  }
  return Array.from(platformSet);
}

function allGames() {
  return KNOWN_GAMES.map(game => {
    return { id: game.id, name: game.name.trim() };
  });
}

function getPostId(uri) {
  // "uri": "at://did:plc:sden5674t33reyexxna44ytg/app.bsky.feed.post/3lyls2ptkbk2q",
  const match = uri.match(/\/app\.bsky\.feed\.post\/([^/]+)/);
  return match ? match[1] : null;
}

function calculateExpiry(expiryStr, createdAt) {
  if (!expiryStr) return null;

  // Check for YYYY-MM-DD format
  let ts = toUnixTimestamp(expiryStr);
  if (ts) return ts;

  // Check for "in X days" or "in X hours"
  let match = expiryStr.match(/(\d+)\s+(days?|hours?)/i);
  if (match && createdAt) {
    let value = parseInt(match[1], 10);
    let unit = match[2].toLowerCase();

    if (unit === "days" || unit === "day") {
      return Math.floor(createdAt / 1000) + value * 24 * 60 * 60;
    } else if (unit === "hours" || unit === "hour") {
      return Math.floor(createdAt / 1000) + value * 60 * 60;
    }
  }

  return null;
}

let post = msg.payload.post;

if (!post || !post.record || !post.record.text) {
  msg.data = msg.payload;
  msg.payload = "Unexpected Payload";
  throw "Unexpected Payload";
}

// Example inputs separated by -----
/*
ZRR3T-56WRJ-JBBTB-TJBJT-XZF3X

Golden keys/skeleton keys for Borderlands, Borderlands 2, Borderlands: The Pre-Sequel, Borderlands 3 and Tiny Tina’s Wonderlands

Expires 2025-09-11

----

ZRR3T-56WRJ-JBBTB-TJBJT-XZF3X

Golden keys/skeleton keys for Borderlands, Borderlands 2, Borderlands: The Pre-Sequel, Borderlands 3 and Tiny Tina’s Wonderlands

Expires in 10 hours

----

T9RJB-BFKRR-3RBTW-B33TB-KCZB9

1 golden key for Borderlands 4 🎉

Expiry unknown

-----

ZRR3T-56WRJ-JBBTB-TJBJT-XZF3X

Golden keys/skeleton keys for Borderlands, Borderlands 2, Borderlands: The Pre-Sequel, Borderlands 3 and Tiny Tina’s Wonderlands

Expires 2025-09-11

-----

WHWJB-XH3SX-39CZW-H3BBB-BTF55

1 golden key for Borderlands 4.

Unknown expiry
-----
WHKJJ-SXJHR-39CS5-9JJBT-595B9

5 golden keys for Borderlands, Borderlands 2, Borderlands: The Pre-Sequel and Borderlands 3, plus a diamond key for Borderlands 3

-----

HRFTJ-XBB63-33T33-TB3JB-H5W59

3 golden/skeleton keys
BL, BL2, BL:TPS, BL3, TTWL
-----
HX63J-9JT63-BJBTB-TB333-RZXFW

3 golden keys for BL, BL2, BLTPS, BL3 and TTWL

----
BSRT3-FTZBJ-K6BTW-JB3T3-WXT99

3ZXJB-53STT-56T3W-B3TT3-HTS95

1 golden key each for Borderlands 4.

Expires in 40 hours.
*/

let input = post.record.text;
let source = null;
let postId = getPostId(post.uri);
if (postId) {
  source = `https://bsky.app/profile/shift.jedillama.social/post/${postId}`;
}

// let regex = /(?<code>(?:[A-Z0-9]{5}-){4}[A-Z0-9]{5})[\s\S]*?(?:(?<reward>.+?)(?:\s+each)?\s+for\s+(?<games>.+))?(?:\n+Expires\s+(?:in\s+)?(?<expiry>(?:\d{4}-\d{2}-\d{2}|\d{1,}(?:\s+days|\s+hours))))?(?!\n+(?:[A-Z0-9]{5}-){4}[A-Z0-9]{5}|$)/gmi;

let regex = /(?<code>(?:[A-Z0-9]{5}-){4}[A-Z0-9]{5})\s*?\n+(?:(?<reward>.+)?(?:(?:\s+each)?(?:\s+for\s+|\n)(?<games>.+))\n+)?(?:Unknown\sExpiry)?(?:(?:Expires|Expiry)\s+(?:in\s+)?(?<expiry>(?:\d{4}-\d{2}-\d{2}|\d{1,}(?:\s+days|\s+hours))|unknown))?/gmi;

created = post.record.createdAt ? toUnixTimestamp(post.record.createdAt.split("T")[0]) : Math.floor(Date.now() / 1000);

let results = [];
let resultCodes = []
let resultGames = [];
let resultReward = "";
let resultExpiry = null;


while ((match = regex.exec(input)) !== null) {
  let code = match.groups.code.trim().toUpperCase().replace(/ /g, "");
  let reward = match.groups.reward;
  let expiry = match.groups.expiry ? match.groups.expiry : null;
  let matchGames = match.groups.games
    ? match.groups.games.split(/\s*,\s*|\s+and\s+/).map(s => s.trim()).filter(Boolean)
    : [];

  if (!code || resultCodes.includes(code)) {
    continue;
  }

  resultCodes.push(code);

  // if there are multiple matches, the first one will not have expiry, games, or reward
  if (reward) {
    resultReward = reward.trim();
  }

  if (expiry) {
    resultExpiry = expiry.trim();
  }

  if (matchGames.length > 0) {
    // Map to game objects, filter out nulls, and remove duplicates by id
    let mappedGames = matchGames.map(cleanGame).filter(Boolean);
    let uniqueGames = [];
    let seenIds = new Set();
    for (let g of mappedGames) {
      if (!seenIds.has(g.id)) {
        uniqueGames.push(g);
        seenIds.add(g.id);
      }
    }
    resultGames = uniqueGames;
  }
}

if (resultGames.length === 0) {
  resultGames = allGames();
}

for (let code of resultCodes) {
  results.push({
    code: code,
    reward: resultReward,
    games: resultGames,
    platforms: getAllPlatforms(resultGames),
    expiry: calculateExpiry(resultExpiry) || null,
    source: source,
    source_id: "bsky-gbsc-nodered",
    notes: `Posted by ${post.author.displayName} (@${post.author.handle}) on Bluesky`,
    created_at: created
  });
}


msg.payload = results;
return msg;
