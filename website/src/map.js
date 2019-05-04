/* globals tm, google */
import './css/map.scss';

customElements.define('tm-map', class extends HTMLElement {
	connectedCallback() {
		window.initMap = () => {
			tm.map = new google.maps.Map(
				this,
				{
					center: {lat: 39.8333333, lng: -98.585522},
					zoom: 5
				}
			);

			tm.highlighted_icon = {
					fillColor: "#F77",
					fillOpacity: 1,
					strokeColor: "#222",
					strokeWeight: 1,
					path: google.maps.SymbolPath.CIRCLE,
					scale: 10
				};
			tm.default_icon = {
					fillColor: "#F88",
					fillOpacity: .7,
					strokeColor: "#222",
					strokeWeight: 1,
					path: google.maps.SymbolPath.CIRCLE,
					scale: 10
				};
		};

		let script = document.createElement('script');
		script.async = false;
		script.src = "https://maps.googleapis.com/maps/api/js?key=AIzaSyB2qLQUWCQ-IcHvOFHdxmFvCdzQ5wqt73I&callback=initMap"
		document.getElementsByTagName('body')[0].appendChild(script);
	}
});
