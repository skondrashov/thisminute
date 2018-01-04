import React, { Component } from 'react';
import TweetBlock from './TweetBlock';
import { DragDropContext } from 'react-dnd';
import HTML5Backend from 'react-dnd-html5-backend';

class TweetList extends Component {
  render() {
    return (
      <div className="tweet-list">
        <TweetBlock />
        <TweetBlock />
        <TweetBlock />
        <TweetBlock />
        <TweetBlock />
      </div>
    );
  }
}

export default TweetList;
