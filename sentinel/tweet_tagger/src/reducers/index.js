import { combineReducers } from 'redux';
import TweetListReducer from './reducer_tweetlist';
import CategoryBlockReducer from './reducer_categoryBlockTweets';

// Get Tweet api call
// http://thisminute.org/sentinel/get_tweet.php?n=5
const rootReducer = combineReducers({
  TweetListReducer,
  CategoryBlockReducer
});

export default rootReducer;
