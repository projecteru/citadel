<%inherit file="/base.mako"/>
<%namespace name="utils" file="/utils.mako"/>

<%def name="title()">
  ${ release.name } @ ${ release.sha[:7] }
</%def>

<%!
  from humanfriendly import parse_size
%>

<%def name="more_css()">
  .progress-bar {
  -webkit-transition: none !important;
  transition: none !important;
  }
</%def>

<%block name="main">

  <%call expr="utils.panel()">
    <%def name="header()">
      <h3 class="panel-title">Release</h3>
    </%def>
    <h4><a href="${ url_for('app.app', name=app.name) }">${ app.name }</a> @ ${ release.short_sha }</h4>
    <p>
      ${ release.author } : ${ release.commit_message }
    </p>
    <p>image: ${ release.image }</p>
    % if release.raw:
      <button class="btn btn-info pull-right" data-toggle="modal" data-target="#add-container-modal">
        <span class="fui-plus"></span> Add Raw Container
      </button>
    % elif not release.image:
      <span title="去gitlab pipelines上盯着看，它好我也好，不行的话先重试">
        <a class="btn btn-xs btn-info disabled" href="${ url_for('app.release', name=release.name, sha=release.sha) }" >
          <span class="fui-time" ></span> Building...
        </a>
      </span>
    % else:
      <button class="btn btn-info pull-right" data-toggle="modal" data-target="#add-container-modal">
        <span class="fui-plus"></span> Add Container
      </button>
    % endif
  </%call>

  <%call expr="utils.panel()">
    <%def name="header()">
      <h3 class="panel-title">app.yaml</h3>
    </%def>

    <pre>${ release.specs_text | n }</pre>
  </%call>

  <%
    containers = release.get_container_list(zone=g.zone)
  %>

  <%call expr="utils.panel()">
    <%def name="header()">
      <h3 class="panel-title">Online Containers: ${ len(containers) }</h3>
    </%def>
    <%utils:container_list containers="${ containers }">
    </%utils:container_list>
  </%call>

</%block>

<%def name="more_body()">

  <%call expr="utils.modal('add-container-modal')">

    <%def name="header()">
      <h3 class="modal-title">Add Container</h3>
    </%def>

    % if combos_list:

      <ul class="nav nav-tabs" id="add-container-form">

        <%
          active_ = {'active': 'active'}
        %>
          % for mode, combo in combos_list:
            <li class="${ active_.pop('active', '') }"><a class="btn" data-target="#${ mode }" data-toggle="tab">${ mode }</a></li>
          % endfor

        </ul>

        <div class="tab-content">
          <% active_ = {'active': 'active'} %>
            % for mode, combo in combos_list:
              <div class="tab-pane ${ active_.pop('active', '') }" id="${ mode }">
                <br>

                <form id="add-container-form" class="form-horizontal" action="">
                  <div class="form-group collapse advance-form-group">
                    <label class="col-sm-2 control-label" for="">Release</label>
                    <div class="col-sm-10">
                      <input class="form-control" type="text" name="release" value="${ release.name } / ${ release.short_sha }" data-id="${ release.id }" disabled>
                    </div>
                  </div>
                  <div class="form-group">
                    <label class="col-sm-2 control-label" for="">Pod</label>
                    <div class="col-sm-10">
                      <select name="pod" class="form-control">
                        <option value="${ combo.podname }">${ combo.podname }</option>
                        % for p in [p for p in pods if p.name != combo.podname]:
                          <option value="${ p.name }">${ p.name }</option>
                        % endfor
                      </select>
                    </div>
                  </div>
                  <div class="form-group collapse advance-form-group">
                    <label class="col-sm-2 control-label" for="">Node</label>
                    <div class="col-sm-10">
                      <select class="form-control" name="node" hidden>
                      </select>
                    </div>
                  </div>
                  <div class="form-group">
                    <label class="col-sm-2 control-label" for="">Entrypoint</label>
                    <div class="col-sm-10">
                      <select class="form-control" name="entrypoint">
                        <option value="${ combo.entrypoint }">${ combo.entrypoint }</option>
                        % for entry in [s for s in release.specs.entrypoints.keys() if s != combo.entrypoint]:
                          <option value="${ entry }">${ entry }</option>
                        % endfor
                      </select>
                    </div>
                  </div>
                  <div class="form-group">
                    <label class="col-sm-2 control-label" for="">Env</label>
                    <div class="col-sm-10">
                      <select class="form-control" name="envname">
                        <option value="${ combo.envname }">${ combo.envname }</option>
                      </select>
                    </div>
                  </div>
                  <div class="form-group">
                    <label class="col-sm-2 control-label" for="">几个？</label>
                    <div class="col-sm-10">
                      <input class="form-control" type="number" name="count" value="${ combo.count }">
                    </div>
                  </div>
                  <div class="form-group collapse advance-form-group">
                    <label class="col-sm-2 control-label" for="">CPU</label>
                    <div class="col-sm-10">
                      <select class="form-control" name="cpu">
                        <option value="${ combo.cpu }" type="number">${ combo.cpu }</option>
                        % for cpu_value in [n for n in (0.5, 1, 2, 4, 8) if float(n) != combo.cpu]:
                          <option value="${ cpu_value }" type="number">${ cpu_value }</option>
                        % endfor
                      </select>
                    </div>
                  </div>
                  <div class="form-group collapse advance-form-group">
                    <label class="col-sm-2 control-label" for="">Memory</label>
                    <div class="col-sm-10">
                      <select class="form-control" name="memory">
                        <option value="${ combo.memory }">${ combo.memory_str }</option>
                        % for memory_value in [s for s in ('256MiB', '512MiB', '1GiB', '2GiB', '4GiB', '8GiB', '16GiB') if parse_size(s, binary=True) != combo.memory]:
                          <option value="${ memory_value }">${ memory_value }</option>
                        % endfor
                      </select>
                    </div>
                  </div>
                  <div class="form-group collapse advance-form-group">
                    <label class="col-sm-2 control-label" for="">Extra Env</label>
                    <div class="col-sm-10">
                      <input class="form-control" type="text" name="extra_env" value="${ combo.env_string }">
                    </div>
                  </div>
                  <div class="form-group">
                    <label class="col-sm-2 control-label" for="">Network</label>
                    <div class="col-sm-10">
                      % for name in combo.networks:
                        <label class="checkbox" for="">
                          <input type="checkbox" name="network" value="${ name }" checked="checked">${ name }
                        </label>
                      % endfor
                    </div>
                  </div>
                  <div class="form-group collapse advance-form-group">
                    <label class="col-sm-2 control-label" for="">Debug</label>
                    <div class="col-sm-10">
                      <input class="form-control" type="checkbox" name="debug" value="">
                    </div>
                  </div>
                </form>

              </div>
            % endfor
          </div>

        % else:

          <form id="add-container-form" class="form-horizontal" action="">
            <div class="form-group collapse advance-form-group">
              <label class="col-sm-2 control-label" for="">Release</label>
              <div class="col-sm-10">
                <input class="form-control" type="text" name="release" value="${ release.name } / ${ release.short_sha }" data-id="${ release.id }" disabled>
              </div>
            </div>
            <div class="form-group">
              <label class="col-sm-2 control-label" for="">Pod</label>
              <div class="col-sm-10">
                <select name="pod" class="form-control">
                  % for p in pods:
                    <option value="${ p.name }">${ p.name }</option>
                  % endfor
                </select>
              </div>
            </div>
            <div class="form-group collapse advance-form-group">
              <label class="col-sm-2 control-label" for="">Node</label>
              <div class="col-sm-10">
                <select class="form-control" name="node">
                </select>
              </div>
            </div>
            <div class="form-group">
              <label class="col-sm-2 control-label" for="">Entrypoint</label>
              <div class="col-sm-10">
                <select class="form-control" name="entrypoint">
                  % for entry in release.specs.entrypoints.keys():
                    <option value="${ entry }">${ entry }</option>
                  % endfor
                </select>
              </div>
            </div>
            <div class="form-group">
              <label class="col-sm-2 control-label" for="">Env</label>
              <div class="col-sm-10">
                <select class="form-control" name="envname">
                  % for envname in app.get_env_sets():
                    <option value="${ envname }">${ envname }</option>
                  % endfor
                </select>
              </div>
            </div>
            <div class="form-group collapse advance-form-group">
              <label class="col-sm-2 control-label" for="">几个？</label>
              <div class="col-sm-10">
                <input class="form-control" type="number" name="count" value="1">
              </div>
            </div>
            <div class="form-group collapse advance-form-group">
              <label class="col-sm-2 control-label" for="">CPU</label>
              <div class="col-sm-10">
                <select class="form-control" name="cpu">
                  % for cpu_value in (0.5, 1, 2, 4, 8):
                    <option value="${ cpu_value }" type="number">${ cpu_value }</option>
                  % endfor
                </select>
              </div>
            </div>
            <div class="form-group collapse advance-form-group">
              <label class="col-sm-2 control-label" for="">Memory</label>
              <div class="col-sm-10">
                <select class="form-control" name="memory">
                  % for memory_value in ('256MiB', '512MiB', '1GiB', '2GiB', '4GiB', '8GiB', '16GiB'):
                    <option value="${ memory_value }">${ memory_value }</option>
                  % endfor
                </select>
              </div>
            </div>
            <div class="form-group collapse advance-form-group">
              <label class="col-sm-2 control-label" for="">Extra Env</label>
              <div class="col-sm-10">
                <input class="form-control" type="text" name="extra_env" value="" placeholder="例如a=1;b=2;">
              </div>
            </div>
            <div class="form-group">
              <label class="col-sm-2 control-label" for="">Network</label>
              <div class="col-sm-10" id="network-checkbox">
              </div>
            </div>
            <div class="form-group collapse advance-form-group">
              <label class="col-sm-2 control-label" for="">Debug</label>
              <div class="col-sm-10">
                <input class="form-control" type="checkbox" name="debug" value="">
              </div>
            </div>
          </form>

        % endif

        <%def name="footer()">
          <button class="btn btn-warning pull-left" data-toggle="collapse" data-target=".advance-form-group">老子搞点高级的</button>
          <button class="btn btn-warning" id="close-modal" data-dismiss="modal"><span class="fui-cross"></span>Close</button>
          <button class="btn btn-info" id="add-container-button"><span class="fui-plus"></span>Go</button>
        </%def>

  </%call>

  <%call expr="utils.modal('container-progress', dialog_class='modal-lg')">
    <%def name="header()">
      <h3 class="modal-title">Please wait...</h3>
    </%def>
    <%def name="footer()">
    </%def>

    <pre id="add-container-pre"></pre>

  </%call>

</%def>

<%def name="bottom_script()">
  <script src="/citadel/static/js/deploy.js" type="text/javascript"></script>
  <script>
    $(function(){
      $('[data-toggle="tooltip"]').tooltip();
    });
  </script>
</%def>
