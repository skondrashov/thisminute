<!doctype html>
<html ng-app="trendmap">

    <head>
<!--    <base href="/"> -->

    <script src="https://code.jquery.com/jquery-2.1.1.min.js"></script>
    <script src="//ajax.googleapis.com/ajax/libs/jqueryui/1.10.4/jquery-ui.min.js"></script>

    <!-- Angular -->
    <script src="https://ajax.googleapis.com/ajax/libs/angularjs/1.4.6/angular.js"></script>
    <script src="https://ajax.googleapis.com/ajax/libs/angularjs/1.2.25/angular-route.js"></script>
    <script src="//code.angularjs.org/1.2.12/angular-animate.min.js"></script>
    <script src="//code.angularjs.org/1.2.12/angular-sanitize.min.js"></script>

    <script src="js/vendors/materialize.js"></script>

    <!-- JS files -->
    <script src="js/TestData.js"></script>
    <script src="js/Objects.js"></script>
    <script src="js/MainController.js"></script>
    <script src="js/directives.js"></script>
    <script src="js/pages/TrendMap.js"></script>
    <script src="js/pages/EventList.js"></script>

    <!-- StyleSheets -->
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
    <link rel="stylesheet" type="text/css" href="css/materialize.css">
    <link rel="stylesheet" type="text/css" href="css/main.css">
    <link rel="stylesheet" type="text/css" href="css/animations.css">

  </head>

  <body ng-controller="MainCtrl as main">
    <span ng-view class="content"></span>
  </body>

</html>