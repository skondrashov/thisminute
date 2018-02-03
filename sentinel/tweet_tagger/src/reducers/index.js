import { combineReducers } from 'redux';
import TweetListReducer from './reducer_tweetlist';

const rootReducer = combineReducers({
  TweetListReducer,
  //TweetArraysReducer
});

export default rootReducer;
