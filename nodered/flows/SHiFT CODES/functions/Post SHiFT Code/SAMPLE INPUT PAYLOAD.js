let SAMPLE_PAYLOAD = {
  games: [
    {
      id: 'ttw',
      name: 'Tiny Tina\'s Wonderlands'
    }
  ],
  code: 'XXXXX-XXXXX-XXXXX-XXXXX-XXXXX',
  platforms: [
    'XBOX',
    'Epic',
    'Steam'
  ],
  expiry: null, // null or number
  reward: '3 Skeleton Keys',
  notes: '',
  source: 'https://store.epicgames.com/en-US/news/grab-free-loot-with-our-borderlands-shift-codes-guide',
  created_at: 1757777975,
};
msg.payload = SAMPLE_PAYLOAD;
return msg;
