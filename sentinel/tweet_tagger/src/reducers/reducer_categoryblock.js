/* eslint-disable */
import { DROP_IN_CATEGORY } from '../actions/index';

export default function(state = [], action) {
  switch(action.type) {
    case DROP_IN_CATEGORY:
      console.log(action.payload);
      console.log("Passed through reducer_categoryblock");
  }
  return state;
}
