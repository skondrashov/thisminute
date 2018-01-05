import React, { Component } from 'react';
import CategoryBlock from './CategoryBlock';

class CategoryList extends Component {
  render() {
    return (
      <div className="category-block">
        <CategoryBlock />
        <CategoryBlock />
        <CategoryBlock />
      </div>
    );
  }
}

export default CategoryList;
