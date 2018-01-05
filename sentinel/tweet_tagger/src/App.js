import React, { Component } from 'react';
import { DragDropContext } from 'react-dnd';
import HTML5Backend from 'react-dnd-html5-backend';
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

export default DragDropContext(HTML5Backend)(App);
