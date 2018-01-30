import { FETCH_NEW_TWEET } from '../actions/index';

export function fetchNewTweet() {
  const payload = {
    tweet: "this should be a tweet from the db"
  };

  return {
    type: FETCH_NEW_TWEET,
    payload: payload
  };
}
