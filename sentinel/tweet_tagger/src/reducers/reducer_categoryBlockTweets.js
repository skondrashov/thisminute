/* eslint-disable */
import { DROP_IN_CATEGORY } from '../actions/index';

export default function( state = { categoryBlockTweets: [] }, action) {
  switch(action.type) {
    case DROP_IN_CATEGORY:
      return {...state, categoryBlockTweets: state.categoryBlockTweets.concat(action.payload.tweet) };
  }
  return state;
}
