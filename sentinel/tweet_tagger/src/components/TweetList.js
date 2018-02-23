import React, { Component } from 'react';
import TweetBlock from './TweetBlock';
import axios from 'axios';

class TweetList extends Component {
  constructor(props) {
    super(props);

    this.state = { tweets: [] };
  }

  // TODO: Use a better search algo to find the element to remove
  // could keep array sorted by ID and use binary search
  _removeFromTweetList(tweet) {
    this.setState({ tweets: this.state.tweets.filter(e => e.id !== tweet.tweet.id) });
  }

  _renderTweetBlocks(tweetArray) {
    return this.state.tweets.map((tweet, i) => {
      return(
        <TweetBlock
          tweet={tweet}
          key={i}
          _removeFromTweetList={tweet => this._removeFromTweetList(tweet)}
        />
      );
    });
  }

// TODO: Get IDs for tweets from database, not Math.random
  _getNewTweet() {
    const url = 'http://thisminute.org/sentinel/get_tweet.php?n=1';

    axios.get(url)
      .then((response) => {
        this.setState({ tweets: [...this.state.tweets, { id: Math.random(), content: response.data[0] }] });
      })
  }

  render() {
    return (
      <div className="tweet-list">
        <button onClick={event => this._getNewTweet()}>Get Tweet</button>
        {this._renderTweetBlocks()}
      </div>
    );
  }
}

export default TweetList;
