import React, { Component } from 'react';
import TweetBlock from './TweetBlock';

class TweetList extends Component {
  render() {
    return (
      <div className="row tweet-list">
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
