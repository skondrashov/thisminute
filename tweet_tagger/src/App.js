import React, { Component } from 'react';
import './App.css';
import TweetList from './containers/TweetList';

class App extends Component {
  render() {
    return (
      <div>
        <TweetList />
      </div>
    );
  }
}

export default App;
