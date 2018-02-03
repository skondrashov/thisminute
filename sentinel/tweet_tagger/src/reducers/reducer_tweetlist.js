/* eslint-disable */
import { DROP_IN_CATEGORY } from '../actions/index';

export default function( state = {
    tweetListTweets: [
    {username: "user1", content: "content1", tweet_id: "1"},
    {username: "user2", content: "content2", tweet_id: "2"},
    {username: "user3", content: "content3", tweet_id: "3"},
    {username: "user4", content: "content4", tweet_id: "4"},
    {username: "user5", content: "content5", tweet_id: "5"}]
  }, action) {
  switch(action.type) {
    case DROP_IN_CATEGORY:
      const id = action.payload.tweet.tweet_id;
      return { tweetListTweets: state.tweetListTweets.filter(tweet => tweet.tweet_id != id) };
  }
  return state;
}
