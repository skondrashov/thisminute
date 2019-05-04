import React from 'react';
import ReactDOM from 'react-dom';
import './css/index.scss';
import * as serviceWorker from './serviceWorker';

import './globals'
import './map';
import Sidebar from './sidebar';

serviceWorker.unregister();

let App = (props) =>
<>
	<tm-map/>
	<Sidebar/>
</>

ReactDOM.render(<App />, document.getElementById('root'));
