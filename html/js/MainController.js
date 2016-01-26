var app = angular.module("trendmap", ['ngRoute', 'ui.materialize', 'infinite-scroll']);
var app_server = "http://" + window.location.host + "/";

app.controller("MainCtrl", ["$scope", "$http",
    function($scope, $http) {
        
        $('ul_tabs').tabs();    
        
        $http({
            url: app_server + "press/get_event_list.php",
            method: "GET",
        }).
        success(function(data) {
            console.log("Successfully retrieved data");
        }).
        error(function(data) {
            console.error("Error retrieving data");     
        });
                    
    }]);

app.config(function($routeProvider) { // include this for pretty URL $locationProvider
    $routeProvider
    
    
    .when('/', {
        templateUrl : 'html/pages/Home.html',
        controller : 'MainCtrl'
    })
    
    .when('/TrendMap', {
        templateUrl : 'html/pages/TrendMap.html',
        controller : 'TrendMapCtrl'
    })
    
    .when('/EventList', {
        templateUrl : 'html/pages/EventListCtrl.html',
        controller : 'EventListCtrl'
    })

});