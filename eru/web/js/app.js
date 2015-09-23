'use strict'

angular.module('eru', ['ngRoute'])

  .config(function ($routeProvider) {
    $routeProvider
      .when('/', {
        templateUrl: 'templates/pods.html',
        controller: 'PodsController',
      })
      .when('/pods/', {
        templateUrl: 'templates/pods.html',
        controller: 'PodsController',
      })
      .when('/app/:appname/versions/', {
        templateUrl: 'templates/versions.html',
        controller: 'AppVersionsController',
      })
      .when('/app/:appname/containers/', {
        templateUrl: 'templates/containers.html',
        controller: 'AppContainersController',
      })
      .when('/pod/:podname/hosts/', {
        templateUrl: 'templates/pod_hosts.html',
        controller: 'PodHostsController',
      })
      .when('/host/:hostname/containers/', {
        templateUrl: 'templates/containers.html',
        controller: 'HostContainersController',
      })
      .when('/host/:hostname/macvlan/', {
        templateUrl: 'templates/host_macvlan.html',
        controller: 'HostMacvlanController',
      })
      .when('/network/list/', {
        templateUrl: 'templates/network.html',
        controller: 'NetworkController',
      })
  })

  .controller('PodsController', function ($scope, $http) {
    $http.get('/api/pod/list/').success(function (r) {
      $scope.pods = r;
    }).error(function (){
      $scope.pods = [];
    });
  })

  .controller('AppVersionsController', function ($scope, $http, $routeParams) {
    $scope.versions = [];
    $http.get('/api/app/' + $routeParams.appname + '/versions/').success(function (r) {
      if (!r.r) {
        $scope.versions = r.versions;
      }
    });
  })

  .controller('AppContainersController', function ($scope, $http, $routeParams) {
    $scope.containers = [];
    $http.get('/api/app/' + $routeParams.appname + '/containers/').success(function (r) {
      if (!r.r) {
        $scope.containers = r.containers;
      }
    });
  })

  .controller('PodHostsController', function ($scope, $http, $route, $routeParams) {
    $scope.$route = $route;
    $scope.$routeParams = $routeParams;
    $http.get('/api/pod/' + $routeParams.podname + '/hosts/').success(function (r) {
      $scope.hosts = r;
    }).error(function (){
      $scope.hosts = [];
    });
  })

  .controller('HostContainersController', function ($scope, $routeParams, $http) {
    $scope.hosts = [];
    $http.get('/api/host/' + $routeParams.hostname + '/containers/').success(function (r) {
      if (!r.r) {
        $scope.containers = r.containers;
      }
    });
  })

  .controller('HostMacvlanController', function ($scope, $routeParams, $http) {
    $scope.vlans = [];
    $http.get('/api/host/' + $routeParams.hostname + '/macvlan/').success(function (r) {
      $scope.vlans = r;
    });
  })

  .controller('NetworkController', function ($scope, $http) {
    $scope.networks = [];
    $http.get('/api/network/list/').success(function (r) {
      $scope.networks = r;
    });
  });
