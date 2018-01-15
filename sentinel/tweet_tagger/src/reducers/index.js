import { combineReducers } from 'redux';
import TweetListReducer from './reducer_tweetlist';
import CategoryBlockReducer from './reducer_categoryblock';

const rootReducer = combineReducers({
  TweetListReducer,
  CategoryBlockReducer
});

export default rootReducer;
