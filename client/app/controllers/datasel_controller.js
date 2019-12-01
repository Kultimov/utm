import angular from 'angular';
import {CONTROLLERS_MODULE_NAME} from "../const";

const CONTROLLER_NAME = "DataSelectionCtrl";

class DataSelectionCtrl {

  constructor($scope, GtfsService, $rootScope) {
    
    this.$scope = $scope;
    this.GtfsService = GtfsService;
    this.$rootScope = $rootScope;
    this.$scope.dbfnameupdate = () => {
      this.$rootScope.appdata.dbfname = this.$scope.selected_dbfname;
      this.$rootScope.appdata.show_footer = true;
      this.$rootScope.appdata.show_data_select = false;
      this.GtfsService.fetch_stats();
    };
  }
}

var controllersModule = angular.module(CONTROLLERS_MODULE_NAME);
controllersModule.controller(CONTROLLER_NAME, ['$scope', 'GtfsService', '$rootScope', DataSelectionCtrl]);
export default CONTROLLER_NAME;
