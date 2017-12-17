import React, { Component } from 'react';
import CategoryBlock from './CategoryBlock';

class CategoryList extends Component {
  render() {
    return (
      <div className="row">
        <CategoryBlock />
        <CategoryBlock />
        <CategoryBlock />
      </div>
    );
  }
}

export default CategoryList;
