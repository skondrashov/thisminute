export const DROP_IN_CATEGORY = 'DROP_IN_CATEGORY';

export function dropInCategory(tweet, category) {

  console.log("Dropped tweet with id " + tweet.tweet_id + " in category " + category);

  const payload = {
    tweet: tweet,
    category: category
  };

  return {
    type: DROP_IN_CATEGORY,
    payload: payload
  };
}
