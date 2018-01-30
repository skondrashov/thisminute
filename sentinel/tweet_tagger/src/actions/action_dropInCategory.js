import { DROP_IN_CATEGORY } from '../actions/index';

export function dropInCategory(tweet, dropAt) {
  console.log("Dropped tweet with id " + tweet.tweet_id + " in category " + dropAt.category);
  
  const payload = {
    tweet: tweet,
    category: dropAt.category
  };

  return {
    type: DROP_IN_CATEGORY,
    payload: payload
  };
}
