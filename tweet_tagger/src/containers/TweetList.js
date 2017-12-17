import React, { Component } from 'react';
import TweetBlock from './TweetBlock';

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
