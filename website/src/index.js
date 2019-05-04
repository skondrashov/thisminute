import React, {Component} from 'react';
import ReactDOM from 'react-dom';
import './css/index.scss';
import * as serviceWorker from './serviceWorker';

import './globals'
import './map';
import Sidebar from './sidebar';

// If you want your app to work offline and load faster, you can change
// unregister() to register() below. Note this comes with some pitfalls.
// Learn more about service workers: https://bit.ly/CRA-PWA
serviceWorker.unregister();

class App extends Component {
	render() {
		return (<>
			<tm-map/>
			<Sidebar/>
		</>);
	}
}

ReactDOM.render(<App />, document.getElementById('root'));
