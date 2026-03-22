/**
 * 统一导出所有 API 模块
 */

import * as siteApi from './modules/site'
import * as resourceApi from './modules/resource'
import * as downloadApi from './modules/download'
import * as subscriptionApi from './modules/subscription'
import * as notificationApi from './modules/notification'
import * as userApi from './modules/user'
import * as movieApi from './modules/movie'
import * as tvApi from './modules/tv'
import * as identificationApi from './modules/identification'
import * as settingsApi from './modules/settings'
import * as mediaApi from './modules/media'
import * as mediaServerApi from './modules/mediaServer'
import * as organizeApi from './modules/organize'
import * as taskApi from './modules/task'
import * as filesystemApi from './modules/filesystem'
import * as adultApi from './modules/adult'
import * as dashboardApi from './modules/dashboard'
import * as aiAgentApi from './modules/aiAgent'
import * as personApi from './modules/person'
import * as loginHistoryApi from './modules/loginHistory'
import * as mcpServerApi from './modules/mcpServer'


export default {
  site: siteApi,
  resource: resourceApi,
  download: downloadApi,
  subscription: subscriptionApi,
  notification: notificationApi,
  user: userApi,
  movie: movieApi,
  tv: tvApi,
  identification: identificationApi,
  settings: settingsApi,
  media: mediaApi,
  mediaServer: mediaServerApi,
  organize: organizeApi,
  task: taskApi,
  filesystem: filesystemApi,
  adult: adultApi,
  dashboard: dashboardApi,
  aiAgent: aiAgentApi,
  person: personApi,
  loginHistory: loginHistoryApi,
  mcpServer: mcpServerApi,
}


export { default as request } from './request'
