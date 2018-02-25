import React, { Component } from 'react';
import './App.css';
import TweetList from './components/TweetList';
import CategoryList from './components/CategoryList';
import { DragDropContext } from 'react-dnd';
import HTML5Backend from 'react-dnd-html5-backend';

class App extends Component {
  render() {
    return (
      <div className="App">
        <TweetList />
        <CategoryList />
      </div>
    );
  }
}

export default DragDropContext(HTML5Backend)(App);
