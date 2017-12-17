import React, { Component } from 'react';
import TweetBlock from './TweetBlock';

class TweetList extends Component {
  render() {
    return (
      <div className="row tweet-list">
        <div className="col-xs-12">
          <TweetBlock />
          <TweetBlock />
        </div>
      </div>
    );
  }
}

export default TweetList;
