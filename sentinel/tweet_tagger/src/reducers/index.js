import { combineReducers } from 'redux';
import TweetListReducer from './reducer_tweetlist';
import TweetArraysReducer from './reducer_tweetArrays';

const rootReducer = combineReducers({
  TweetListReducer,
  TweetArraysReducer
});

export default rootReducer;
