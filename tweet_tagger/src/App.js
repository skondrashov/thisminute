import React, { Component } from 'react';
import './App.css';
import TweetList from './containers/TweetList';
import CategoryList from './containers/CategoryList';

class App extends Component {
  render() {
    return (
      <div>
        <TweetList />
        <CategoryList />
      </div>
    );
  }
}

export default App;
