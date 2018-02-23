import React, { Component } from 'react';
import TweetBlock from './TweetBlock';
import axios from 'axios';

const MAX_NUM_TWEETS = 5;

class TweetList extends Component {
  constructor(props) {
    super(props);

    this.state = { tweets: [] };
  }

  componentDidMount(){
    const url = 'http://thisminute.org/sentinel/get_tweet.php?n=5';

    axios.get(url)
      .then((response) => {
        var newTweets = [];
        for(var tweet of response.data) {
          console.log(tweet);
          let newTweet = { id: Math.random(), content: tweet };
          newTweets.push(newTweet);
        }
        console.log(newTweets);
        this.setState({ tweets: this.state.tweets.concat(newTweets) });
      })
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
    if(this.state.tweets.length < MAX_NUM_TWEETS) {
      const url = 'http://thisminute.org/sentinel/get_tweet.php?n=1';

      axios.get(url)
        .then((response) => {
          this.setState({ tweets: [...this.state.tweets, { id: Math.random(), content: response.data[0] }] });
        });
    }
  }

  render() {
    return (
      <div className="tweet-list">
        {this._renderTweetBlocks()}
        <div>
          <button onClick={event => this._getNewTweet()}>Get Tweet</button>
        </div>
      </div>
    );
  }
}

export default TweetList;
