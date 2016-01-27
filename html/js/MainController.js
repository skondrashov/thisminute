var app = angular.module("trendmap", ['ngRoute', 'ui.materialize', 'infinite-scroll']);
var app_server = "http://" + window.location.host + "/";

app.controller("MainCtrl", ["$scope", "$http",
    function($scope, $http) {
        
        $('ul_tabs').tabs();    
                    
    }]);

app.config(function($routeProvider) { // include this for pretty URL $locationProvider
    $routeProvider
    
    
    .when('/', {
        templateUrl : 'html/pages/Home.html',
        controller : 'MainCtrl'
    })
    
    .when('/Map', {
        templateUrl : 'html/pages/TrendMap.html',
        controller : 'TrendMapCtrl'
    })
    
    .when('/Feed', {
        templateUrl : 'html/pages/EventListCtrl.html',
        controller : 'EventListCtrl'
    })

});