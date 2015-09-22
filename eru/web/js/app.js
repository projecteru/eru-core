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
      .when('/pod/:podname/hosts/', {
        templateUrl: 'templates/pod_hosts.html',
        controller: 'PodHostsController',
      })
      .when('/host/:hostname/containers/', {
        templateUrl: 'templates/host_containers.html',
        controller: 'HostContainersController',
      })
      .when('/host/:hostname/macvlan/', {
        templateUrl: 'templates/host_macvlan.html',
        controller: 'HostMacvlanController',
      })
  })

  .controller('PodsController', function ($scope, $http) {
    $http.get('/api/pod/list/').success(function (r){
      $scope.pods = r;
    }).error(function (){
      $scope.pods = [];
    });
  })

  .controller('PodHostsController', function ($scope, $http, $route, $routeParams) {
    $scope.$route = $route;
    $scope.$routeParams = $routeParams;
    $http.get('/api/pod/' + $routeParams.podname + '/hosts/').success(function (r){
      $scope.hosts = r;
    }).error(function (){
      $scope.hosts = [];
    });
  })

  .controller('HostContainersController', function ($scope, $routeParams, $http) {
    $scope.hosts = [];
    $http.get('/api/host/' + $routeParams.hostname + '/containers/').success(function (r){
      if (!r.r) {
        $scope.containers = r.containers;
      }
    });
  })

  .controller('HostMacvlanController', function ($scope, $routeParams, $http) {
    $scope.vlans = [];
    $http.get('/api/host/' + $routeParams.hostname + '/macvlan/').success(function (r){
      $scope.vlans = r;
    });
  });
