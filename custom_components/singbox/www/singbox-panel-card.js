var U=globalThis,M=U.ShadowRoot&&(U.ShadyCSS===void 0||U.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,D=Symbol(),ot=new WeakMap,E=class{constructor(t,e,i){if(this._$cssResult$=!0,i!==D)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o,e=this.t;if(M&&t===void 0){let i=e!==void 0&&e.length===1;i&&(t=ot.get(e)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),i&&ot.set(e,t))}return t}toString(){return this.cssText}},rt=o=>new E(typeof o=="string"?o:o+"",void 0,D),k=(o,...t)=>{let e=o.length===1?o[0]:t.reduce((i,s,n)=>i+(r=>{if(r._$cssResult$===!0)return r.cssText;if(typeof r=="number")return r;throw Error("Value passed to 'css' function must be a 'css' function result: "+r+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(s)+o[n+1],o[0]);return new E(e,o,D)},at=(o,t)=>{if(M)o.adoptedStyleSheets=t.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(let e of t){let i=document.createElement("style"),s=U.litNonce;s!==void 0&&i.setAttribute("nonce",s),i.textContent=e.cssText,o.appendChild(i)}},j=M?o=>o:o=>o instanceof CSSStyleSheet?(t=>{let e="";for(let i of t.cssRules)e+=i.cssText;return rt(e)})(o):o;var{is:St,defineProperty:Et,getOwnPropertyDescriptor:kt,getOwnPropertyNames:Ct,getOwnPropertySymbols:Tt,getPrototypeOf:Nt}=Object,R=globalThis,lt=R.trustedTypes,Ot=lt?lt.emptyScript:"",Pt=R.reactiveElementPolyfillSupport,C=(o,t)=>o,G={toAttribute(o,t){switch(t){case Boolean:o=o?Ot:null;break;case Object:case Array:o=o==null?o:JSON.stringify(o)}return o},fromAttribute(o,t){let e=o;switch(t){case Boolean:e=o!==null;break;case Number:e=o===null?null:Number(o);break;case Object:case Array:try{e=JSON.parse(o)}catch{e=null}}return e}},ct=(o,t)=>!St(o,t),dt={attribute:!0,type:String,converter:G,reflect:!1,useDefault:!1,hasChanged:ct};Symbol.metadata??=Symbol("metadata"),R.litPropertyMetadata??=new WeakMap;var v=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=dt){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){let i=Symbol(),s=this.getPropertyDescriptor(t,i,e);s!==void 0&&Et(this.prototype,t,s)}}static getPropertyDescriptor(t,e,i){let{get:s,set:n}=kt(this.prototype,t)??{get(){return this[e]},set(r){this[e]=r}};return{get:s,set(r){let a=s?.call(this);n?.call(this,r),this.requestUpdate(t,a,i)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??dt}static _$Ei(){if(this.hasOwnProperty(C("elementProperties")))return;let t=Nt(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(C("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(C("properties"))){let e=this.properties,i=[...Ct(e),...Tt(e)];for(let s of i)this.createProperty(s,e[s])}let t=this[Symbol.metadata];if(t!==null){let e=litPropertyMetadata.get(t);if(e!==void 0)for(let[i,s]of e)this.elementProperties.set(i,s)}this._$Eh=new Map;for(let[e,i]of this.elementProperties){let s=this._$Eu(e,i);s!==void 0&&this._$Eh.set(s,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){let e=[];if(Array.isArray(t)){let i=new Set(t.flat(1/0).reverse());for(let s of i)e.unshift(j(s))}else t!==void 0&&e.push(j(t));return e}static _$Eu(t,e){let i=e.attribute;return i===!1?void 0:typeof i=="string"?i:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),this.renderRoot!==void 0&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){let t=new Map,e=this.constructor.elementProperties;for(let i of e.keys())this.hasOwnProperty(i)&&(t.set(i,this[i]),delete this[i]);t.size>0&&(this._$Ep=t)}createRenderRoot(){let t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return at(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,i){this._$AK(t,i)}_$ET(t,e){let i=this.constructor.elementProperties.get(t),s=this.constructor._$Eu(t,i);if(s!==void 0&&i.reflect===!0){let n=(i.converter?.toAttribute!==void 0?i.converter:G).toAttribute(e,i.type);this._$Em=t,n==null?this.removeAttribute(s):this.setAttribute(s,n),this._$Em=null}}_$AK(t,e){let i=this.constructor,s=i._$Eh.get(t);if(s!==void 0&&this._$Em!==s){let n=i.getPropertyOptions(s),r=typeof n.converter=="function"?{fromAttribute:n.converter}:n.converter?.fromAttribute!==void 0?n.converter:G;this._$Em=s;let a=r.fromAttribute(e,n.type);this[s]=a??this._$Ej?.get(s)??a,this._$Em=null}}requestUpdate(t,e,i,s=!1,n){if(t!==void 0){let r=this.constructor;if(s===!1&&(n=this[t]),i??=r.getPropertyOptions(t),!((i.hasChanged??ct)(n,e)||i.useDefault&&i.reflect&&n===this._$Ej?.get(t)&&!this.hasAttribute(r._$Eu(t,i))))return;this.C(t,e,i)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(t,e,{useDefault:i,reflect:s,wrapped:n},r){i&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,r??e??this[t]),n!==!0||r!==void 0)||(this._$AL.has(t)||(this.hasUpdated||i||(e=void 0),this._$AL.set(t,e)),s===!0&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}let t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[s,n]of this._$Ep)this[s]=n;this._$Ep=void 0}let i=this.constructor.elementProperties;if(i.size>0)for(let[s,n]of i){let{wrapped:r}=n,a=this[s];r!==!0||this._$AL.has(s)||a===void 0||this.C(s,void 0,n,a)}}let t=!1,e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(i=>i.hostUpdate?.()),this.update(e)):this._$EM()}catch(i){throw t=!1,this._$EM(),i}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(t){}firstUpdated(t){}};v.elementStyles=[],v.shadowRootOptions={mode:"open"},v[C("elementProperties")]=new Map,v[C("finalized")]=new Map,Pt?.({ReactiveElement:v}),(R.reactiveElementVersions??=[]).push("2.1.2");var Y=globalThis,ht=o=>o,L=Y.trustedTypes,ut=L?L.createPolicy("lit-html",{createHTML:o=>o}):void 0,vt="$lit$",b=`lit$${Math.random().toFixed(9).slice(2)}$`,bt="?"+b,Ht=`<${bt}>`,x=document,N=()=>x.createComment(""),O=o=>o===null||typeof o!="object"&&typeof o!="function",Z=Array.isArray,Ut=o=>Z(o)||typeof o?.[Symbol.iterator]=="function",F=`[ 	
\f\r]`,T=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,pt=/-->/g,_t=/>/g,y=RegExp(`>|${F}(?:([^\\s"'>=/]+)(${F}*=${F}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),gt=/'/g,ft=/"/g,yt=/^(?:script|style|textarea|title)$/i,Q=o=>(t,...e)=>({_$litType$:o,strings:t,values:e}),p=Q(1),Yt=Q(2),Zt=Q(3),A=Symbol.for("lit-noChange"),_=Symbol.for("lit-nothing"),mt=new WeakMap,$=x.createTreeWalker(x,129);function $t(o,t){if(!Z(o)||!o.hasOwnProperty("raw"))throw Error("invalid template strings array");return ut!==void 0?ut.createHTML(t):t}var Mt=(o,t)=>{let e=o.length-1,i=[],s,n=t===2?"<svg>":t===3?"<math>":"",r=T;for(let a=0;a<e;a++){let d=o[a],l,u,c=-1,h=0;for(;h<d.length&&(r.lastIndex=h,u=r.exec(d),u!==null);)h=r.lastIndex,r===T?u[1]==="!--"?r=pt:u[1]!==void 0?r=_t:u[2]!==void 0?(yt.test(u[2])&&(s=RegExp("</"+u[2],"g")),r=y):u[3]!==void 0&&(r=y):r===y?u[0]===">"?(r=s??T,c=-1):u[1]===void 0?c=-2:(c=r.lastIndex-u[2].length,l=u[1],r=u[3]===void 0?y:u[3]==='"'?ft:gt):r===ft||r===gt?r=y:r===pt||r===_t?r=T:(r=y,s=void 0);let g=r===y&&o[a+1].startsWith("/>")?" ":"";n+=r===T?d+Ht:c>=0?(i.push(l),d.slice(0,c)+vt+d.slice(c)+b+g):d+b+(c===-2?a:g)}return[$t(o,n+(o[e]||"<?>")+(t===2?"</svg>":t===3?"</math>":"")),i]},P=class o{constructor({strings:t,_$litType$:e},i){let s;this.parts=[];let n=0,r=0,a=t.length-1,d=this.parts,[l,u]=Mt(t,e);if(this.el=o.createElement(l,i),$.currentNode=this.el.content,e===2||e===3){let c=this.el.content.firstChild;c.replaceWith(...c.childNodes)}for(;(s=$.nextNode())!==null&&d.length<a;){if(s.nodeType===1){if(s.hasAttributes())for(let c of s.getAttributeNames())if(c.endsWith(vt)){let h=u[r++],g=s.getAttribute(c).split(b),f=/([.?@])?(.*)/.exec(h);d.push({type:1,index:n,name:f[2],strings:g,ctor:f[1]==="."?V:f[1]==="?"?K:f[1]==="@"?J:S}),s.removeAttribute(c)}else c.startsWith(b)&&(d.push({type:6,index:n}),s.removeAttribute(c));if(yt.test(s.tagName)){let c=s.textContent.split(b),h=c.length-1;if(h>0){s.textContent=L?L.emptyScript:"";for(let g=0;g<h;g++)s.append(c[g],N()),$.nextNode(),d.push({type:2,index:++n});s.append(c[h],N())}}}else if(s.nodeType===8)if(s.data===bt)d.push({type:2,index:n});else{let c=-1;for(;(c=s.data.indexOf(b,c+1))!==-1;)d.push({type:7,index:n}),c+=b.length-1}n++}}static createElement(t,e){let i=x.createElement("template");return i.innerHTML=t,i}};function w(o,t,e=o,i){if(t===A)return t;let s=i!==void 0?e._$Co?.[i]:e._$Cl,n=O(t)?void 0:t._$litDirective$;return s?.constructor!==n&&(s?._$AO?.(!1),n===void 0?s=void 0:(s=new n(o),s._$AT(o,e,i)),i!==void 0?(e._$Co??=[])[i]=s:e._$Cl=s),s!==void 0&&(t=w(o,s._$AS(o,t.values),s,i)),t}var W=class{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){let{el:{content:e},parts:i}=this._$AD,s=(t?.creationScope??x).importNode(e,!0);$.currentNode=s;let n=$.nextNode(),r=0,a=0,d=i[0];for(;d!==void 0;){if(r===d.index){let l;d.type===2?l=new H(n,n.nextSibling,this,t):d.type===1?l=new d.ctor(n,d.name,d.strings,this,t):d.type===6&&(l=new X(n,this,t)),this._$AV.push(l),d=i[++a]}r!==d?.index&&(n=$.nextNode(),r++)}return $.currentNode=x,s}p(t){let e=0;for(let i of this._$AV)i!==void 0&&(i.strings!==void 0?(i._$AI(t,i,e),e+=i.strings.length-2):i._$AI(t[e])),e++}},H=class o{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,i,s){this.type=2,this._$AH=_,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=i,this.options=s,this._$Cv=s?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode,e=this._$AM;return e!==void 0&&t?.nodeType===11&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=w(this,t,e),O(t)?t===_||t==null||t===""?(this._$AH!==_&&this._$AR(),this._$AH=_):t!==this._$AH&&t!==A&&this._(t):t._$litType$!==void 0?this.$(t):t.nodeType!==void 0?this.T(t):Ut(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==_&&O(this._$AH)?this._$AA.nextSibling.data=t:this.T(x.createTextNode(t)),this._$AH=t}$(t){let{values:e,_$litType$:i}=t,s=typeof i=="number"?this._$AC(t):(i.el===void 0&&(i.el=P.createElement($t(i.h,i.h[0]),this.options)),i);if(this._$AH?._$AD===s)this._$AH.p(e);else{let n=new W(s,this),r=n.u(this.options);n.p(e),this.T(r),this._$AH=n}}_$AC(t){let e=mt.get(t.strings);return e===void 0&&mt.set(t.strings,e=new P(t)),e}k(t){Z(this._$AH)||(this._$AH=[],this._$AR());let e=this._$AH,i,s=0;for(let n of t)s===e.length?e.push(i=new o(this.O(N()),this.O(N()),this,this.options)):i=e[s],i._$AI(n),s++;s<e.length&&(this._$AR(i&&i._$AB.nextSibling,s),e.length=s)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){let i=ht(t).nextSibling;ht(t).remove(),t=i}}setConnected(t){this._$AM===void 0&&(this._$Cv=t,this._$AP?.(t))}},S=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,i,s,n){this.type=1,this._$AH=_,this._$AN=void 0,this.element=t,this.name=e,this._$AM=s,this.options=n,i.length>2||i[0]!==""||i[1]!==""?(this._$AH=Array(i.length-1).fill(new String),this.strings=i):this._$AH=_}_$AI(t,e=this,i,s){let n=this.strings,r=!1;if(n===void 0)t=w(this,t,e,0),r=!O(t)||t!==this._$AH&&t!==A,r&&(this._$AH=t);else{let a=t,d,l;for(t=n[0],d=0;d<n.length-1;d++)l=w(this,a[i+d],e,d),l===A&&(l=this._$AH[d]),r||=!O(l)||l!==this._$AH[d],l===_?t=_:t!==_&&(t+=(l??"")+n[d+1]),this._$AH[d]=l}r&&!s&&this.j(t)}j(t){t===_?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}},V=class extends S{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===_?void 0:t}},K=class extends S{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==_)}},J=class extends S{constructor(t,e,i,s,n){super(t,e,i,s,n),this.type=5}_$AI(t,e=this){if((t=w(this,t,e,0)??_)===A)return;let i=this._$AH,s=t===_&&i!==_||t.capture!==i.capture||t.once!==i.once||t.passive!==i.passive,n=t!==_&&(i===_||s);s&&this.element.removeEventListener(this.name,this,i),n&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}},X=class{constructor(t,e,i){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=i}get _$AU(){return this._$AM._$AU}_$AI(t){w(this,t)}};var Rt=Y.litHtmlPolyfillSupport;Rt?.(P,H),(Y.litHtmlVersions??=[]).push("3.3.3");var xt=(o,t,e)=>{let i=e?.renderBefore??t,s=i._$litPart$;if(s===void 0){let n=e?.renderBefore??null;i._$litPart$=s=new H(t.insertBefore(N(),n),n,void 0,e??{})}return s._$AI(o),s};var tt=globalThis,m=class extends v{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){let e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=xt(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return A}};m._$litElement$=!0,m.finalized=!0,tt.litElementHydrateSupport?.({LitElement:m});var Lt=tt.litElementPolyfillSupport;Lt?.({LitElement:m});(tt.litElementVersions??=[]).push("4.2.2");var At=k`
    :host {
        display: block;
        font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif);
    }
    .card {
        background: var(--ha-card-background, var(--card-background-color));
        border-radius: var(--ha-card-border-radius, 12px);
        box-shadow: var(--ha-card-box-shadow, none);
        padding: 16px;
        color: var(--primary-text-color);
    }

    /* ---------- header ---------- */
    .header {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 8px;
        margin-bottom: 12px;
    }
    .header h2 {
        margin: 0;
        font-size: 18px;
        font-weight: 600;
        color: var(--primary-text-color);
    }
    .header .meta {
        font-size: 12px;
        color: var(--secondary-text-color);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        flex: 1;
        min-width: 0;
    }
    .header .test-all-btn {
        flex: none;
        display: inline-flex;
        align-items: center;
        gap: 4px;
        border: none;
        border-radius: 8px;
        padding: 5px 10px;
        font-size: 12px;
        font-weight: 500;
        cursor: pointer;
        color: var(--primary-text-color);
        background: var(--secondary-background-color, rgba(0, 0, 0, 0.05));
        transition: background 0.15s ease, opacity 0.15s ease;
    }
    .header .test-all-btn:hover {
        background: var(--primary-color);
        color: var(--text-primary-color, #fff);
    }
    .header .test-all-btn[disabled] {
        opacity: 0.5;
        cursor: default;
        pointer-events: none;
    }
    .header .test-all-btn ha-icon {
        --mdc-icon-size: 14px;
    }

    /* ---------- speed tiles ---------- */
    .speeds {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
        margin-bottom: 14px;
    }
    .tile {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px 12px;
        border-radius: 12px;
        background: var(--secondary-background-color, rgba(0, 0, 0, 0.04));
        min-width: 0;
    }
    .tile ha-icon {
        --mdc-icon-size: 22px;
        flex: none;
    }
    .tile .tile-body {
        min-width: 0;
    }
    .tile .tile-label {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: var(--secondary-text-color);
    }
    .tile .tile-value {
        font-size: 24px;
        font-weight: 600;
        line-height: 1.15;
        font-variant-numeric: tabular-nums;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .tile .tile-value .unit {
        font-size: 13px;
        font-weight: 500;
        color: var(--secondary-text-color);
        margin-left: 3px;
    }
    .tile.up ha-icon { color: #ff7043; }
    .tile.down ha-icon { color: var(--success-color, #2e7d32); }

    /* ---------- totals strip ---------- */
    .totals {
        display: flex;
        flex-wrap: wrap;
        gap: 4px 16px;
        margin-bottom: 14px;
        font-size: 12px;
        color: var(--secondary-text-color);
    }
    .totals .chip-stat {
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .totals .chip-stat b {
        color: var(--primary-text-color);
        font-weight: 600;
        font-variant-numeric: tabular-nums;
    }

    /* ---------- groups ---------- */
    .group {
        margin-top: 14px;
        border-top: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
        padding-top: 12px;
    }
    .group-head {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 10px;
    }
    .group-head .group-name {
        font-size: 14px;
        font-weight: 600;
        color: var(--primary-text-color);
    }
    .group-head .group-current {
        font-size: 12px;
        color: var(--secondary-text-color);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .group-head .group-current b {
        color: var(--primary-color);
        font-weight: 600;
    }
    .group-head .test-btn {
        margin-left: auto;
        flex: none;
        display: inline-flex;
        align-items: center;
        gap: 4px;
        border: none;
        border-radius: 8px;
        padding: 5px 10px;
        font-size: 12px;
        font-weight: 500;
        cursor: pointer;
        color: var(--primary-text-color);
        background: var(--secondary-background-color, rgba(0, 0, 0, 0.05));
        transition: background 0.15s ease, opacity 0.15s ease;
    }
    .group-head .test-btn:hover {
        background: var(--primary-color);
        color: var(--text-primary-color, #fff);
    }
    .group-head .test-btn[disabled] {
        opacity: 0.5;
        cursor: default;
        pointer-events: none;
    }
    .group-head .test-btn ha-icon {
        --mdc-icon-size: 14px;
    }

    .nodes {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
    }
    .node {
        display: inline-flex;
        align-items: stretch;
        border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
        border-radius: 10px;
        overflow: hidden;
        background: transparent;
        transition: border-color 0.15s ease, background 0.15s ease;
    }
    .node:hover {
        border-color: var(--primary-color);
        background: var(--secondary-background-color, rgba(0, 0, 0, 0.05));
    }
    .node.active {
        border-color: var(--primary-color);
        background: color-mix(in srgb, var(--primary-color) 14%, transparent);
    }
    .node.active .node-name {
        font-weight: 600;
        color: var(--primary-color);
    }
    .node-select {
        display: inline-flex;
        align-items: center;
        gap: 7px;
        border: none;
        background: transparent;
        padding: 6px 6px 6px 11px;
        font-size: 13px;
        cursor: pointer;
        color: var(--primary-text-color);
        font-family: inherit;
    }
    .node-name {
        max-width: 180px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .node-name.standalone {
        padding: 6px 0 6px 11px;
    }
    .node-ping {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border: none;
        border-left: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
        background: transparent;
        padding: 0 8px;
        cursor: pointer;
        color: var(--secondary-text-color);
        transition: color 0.15s ease, background 0.15s ease;
    }
    .node-ping:hover {
        color: var(--primary-color);
        background: color-mix(in srgb, var(--primary-color) 10%, transparent);
    }
    .node-ping[disabled] {
        opacity: 0.5;
        cursor: default;
        pointer-events: none;
    }
    .node-ping ha-icon {
        --mdc-icon-size: 15px;
    }
    .ping {
        font-size: 12px;
        font-weight: 600;
        font-variant-numeric: tabular-nums;
        border-radius: 6px;
        padding: 1px 6px;
        background: var(--secondary-background-color, rgba(0, 0, 0, 0.06));
    }
    .ping.good { color: var(--success-color, #2e7d32); }
    .ping.warn { color: #f9a825; }
    .ping.bad { color: var(--error-color, #c62828); }
    .ping.none { color: var(--disabled-text-color); }

    /* ---------- states ---------- */
    .state-msg {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 10px;
        padding: 28px 12px;
        color: var(--secondary-text-color);
        font-size: 14px;
        text-align: center;
    }
    .spinner {
        width: 26px;
        height: 26px;
        border: 3px solid var(--divider-color, rgba(0, 0, 0, 0.2));
        border-top-color: var(--primary-color);
        border-radius: 50%;
        animation: singbox-spin 0.9s linear infinite;
    }
    @keyframes singbox-spin {
        to { transform: rotate(360deg); }
    }
    .footer {
        margin-top: 12px;
        font-size: 11px;
        color: var(--disabled-text-color);
        text-align: right;
    }
    .fallback-note {
        margin-top: 12px;
        padding: 8px 10px;
        border-radius: 8px;
        font-size: 12px;
        line-height: 1.4;
        color: #f9a825;
        background: color-mix(in srgb, #f9a825 12%, transparent);
    }
`;var Bt={loading:{ru:"\u0417\u0430\u0433\u0440\u0443\u0437\u043A\u0430 \u0434\u0430\u043D\u043D\u044B\u0445 sing-box\u2026",en:"Loading sing-box data\u2026"},testAll:{ru:"\u041F\u0440\u043E\u0432\u0435\u0440\u0438\u0442\u044C \u0432\u0441\u0435",en:"Test all"},testing:{ru:"\u0422\u0435\u0441\u0442\u2026",en:"Testing\u2026"},test:{ru:"\u0422\u0435\u0441\u0442",en:"Test"},speedUp:{ru:"\u0417\u0430\u0433\u0440\u0443\u0437\u043A\u0430",en:"Upload"},speedDown:{ru:"\u0421\u043A\u0430\u0447\u0438\u0432\u0430\u043D\u0438\u0435",en:"Download"},selectTitle:{ru:"\u0412\u044B\u0431\u0440\u0430\u0442\u044C {tag}",en:"Select {tag}"},pingTitle:{ru:"\u041F\u0440\u043E\u0432\u0435\u0440\u0438\u0442\u044C \u043F\u0438\u043D\u0433 {tag}",en:"Check ping of {tag}"},errors:{loadFailed:{ru:"\u041D\u0435 \u0443\u0434\u0430\u043B\u043E\u0441\u044C \u0437\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044C \u0434\u0430\u043D\u043D\u044B\u0435: {msg}",en:"Failed to load data: {msg}"},groupsDevice:{ru:"\u0413\u0440\u0443\u043F\u043F\u044B \u043F\u0440\u043E\u043A\u0441\u0438 \u043D\u0435 \u043D\u0430\u0439\u0434\u0435\u043D\u044B: \u043F\u043E device_id \u043D\u0430\u0439\u0434\u0435\u043D\u043E \u0437\u0430\u043F\u0438\u0441\u0435\u0439 \u0440\u0435\u0435\u0441\u0442\u0440\u0430: {count}, \u043D\u043E \u0441\u0443\u0449\u043D\u043E\u0441\u0442\u0435\u0439 ha-singbox \u0441\u0440\u0435\u0434\u0438 \u043D\u0438\u0445 \u043D\u0435\u0442 (select \u0432\u043E \u0432\u0441\u0451\u043C \u0440\u0435\u0435\u0441\u0442\u0440\u0435: {selects}, ping-\u0441\u0435\u043D\u0441\u043E\u0440\u043E\u0432: {pings}). \u041F\u0440\u0438\u043C\u0435\u0440 \u0437\u0430\u043F\u0438\u0441\u0435\u0439 \u043F\u043E device_id: {sample}. \u0423\u0431\u0435\u0434\u0438\u0442\u0435\u0441\u044C, \u0447\u0442\u043E \u0443\u0441\u0442\u0430\u043D\u043E\u0432\u043B\u0435\u043D\u0430 \u0438\u043D\u0442\u0435\u0433\u0440\u0430\u0446\u0438\u044F ha-singbox (Ghost-in-the-dark/ha-singbox) \u0438 \u043E\u043D\u0430 \u0441\u043E\u0437\u0434\u0430\u043B\u0430 \u0441\u0443\u0449\u043D\u043E\u0441\u0442\u0438, \u0437\u0430\u0442\u0435\u043C \u043F\u0435\u0440\u0435\u0437\u0430\u043F\u0443\u0441\u0442\u0438\u0442\u0435 HA.",en:"Proxy groups not found: device_id matched {count} registry records, but none of them are ha-singbox entities (selects across the registry: {selects}, ping sensors: {pings}). Sample records on the device: {sample}. Make sure the ha-singbox integration (Ghost-in-the-dark/ha-singbox) is installed and created entities, then restart HA."},groupsNone:{ru:"\u0413\u0440\u0443\u043F\u043F\u044B \u043F\u0440\u043E\u043A\u0441\u0438 \u043D\u0435 \u043D\u0430\u0439\u0434\u0435\u043D\u044B: \u0432 \u0440\u0435\u0435\u0441\u0442\u0440\u0435 \u043D\u0435\u0442 \u0441\u0443\u0449\u043D\u043E\u0441\u0442\u0435\u0439 sing-box (\u0432\u0441\u0435\u0433\u043E select: {selects}, ping-\u0441\u0435\u043D\u0441\u043E\u0440\u043E\u0432: {pings}). \u041F\u0440\u043E\u0432\u0435\u0440\u044C\u0442\u0435, \u0447\u0442\u043E ha-singbox \u0443\u0441\u0442\u0430\u043D\u043E\u0432\u043B\u0435\u043D\u0430 \u0438 \u043D\u0430\u0441\u0442\u0440\u043E\u0435\u043D\u0430, \u0437\u0430\u0442\u0435\u043C \u043F\u0435\u0440\u0435\u0437\u0430\u043F\u0443\u0441\u0442\u0438\u0442\u0435 HA.",en:"Proxy groups not found: the registry has no sing-box entities (selects in total: {selects}, ping sensors: {pings}). Check that ha-singbox is installed and configured, then restart HA."},groupsBadUid:{ru:"\u0413\u0440\u0443\u043F\u043F\u044B \u043F\u0440\u043E\u043A\u0441\u0438 \u043D\u0435 \u043D\u0430\u0439\u0434\u0435\u043D\u044B: select-\u0441\u0443\u0449\u043D\u043E\u0441\u0442\u0438 \u0435\u0441\u0442\u044C, \u043D\u043E \u0441 \u043D\u0435\u043E\u0436\u0438\u0434\u0430\u043D\u043D\u044B\u043C \u0444\u043E\u0440\u043C\u0430\u0442\u043E\u043C unique_id ({sample}). \u041E\u0431\u043D\u043E\u0432\u0438\u0442\u0435 ha-singbox \u0438 \u043F\u0435\u0440\u0435\u0437\u0430\u043F\u0443\u0441\u0442\u0438\u0442\u0435 HA.",en:"Proxy groups not found: select entities exist but with an unexpected unique_id format ({sample}). Update ha-singbox and restart HA."}},fallback:{device:{ru:"device_id \xAB{device}\xBB \u043D\u0435 \u0434\u0430\u043B \u0433\u0440\u0443\u043F\u043F (\u0437\u0430\u043F\u0438\u0441\u0435\u0439 \u0440\u0435\u0435\u0441\u0442\u0440\u0430: {count}) \u2014 \u043F\u043E\u043A\u0430\u0437\u0430\u043D\u044B \u0432\u0441\u0435 \u044D\u043A\u0437\u0435\u043C\u043F\u043B\u044F\u0440\u044B sing-box.",en:"device_id \u201C{device}\u201D produced no groups ({count} registry records) \u2014 showing all sing-box instances."},entityNotFound:{ru:"entity \xAB{entity}\xBB \u043D\u0435 \u043D\u0430\u0439\u0434\u0435\u043D\u0430 \u0432 \u0440\u0435\u0435\u0441\u0442\u0440\u0435 \u2014 \u043F\u043E\u043A\u0430\u0437\u0430\u043D\u044B \u0432\u0441\u0435 \u044D\u043A\u0437\u0435\u043C\u043F\u043B\u044F\u0440\u044B sing-box.",en:"entity \u201C{entity}\u201D was not found in the registry \u2014 showing all sing-box instances."},entityNoGroups:{ru:"entity \xAB{entity}\xBB \u043D\u0435 \u0434\u0430\u043B\u0430 \u0433\u0440\u0443\u043F\u043F \u2014 \u043F\u043E\u043A\u0430\u0437\u0430\u043D\u044B \u0432\u0441\u0435 \u044D\u043A\u0437\u0435\u043C\u043F\u043B\u044F\u0440\u044B sing-box.",en:"entity \u201C{entity}\u201D produced no groups \u2014 showing all sing-box instances."}},editor:{title:{ru:"\u0417\u0430\u0433\u043E\u043B\u043E\u0432\u043E\u043A",en:"Title"},language:{ru:"\u042F\u0437\u044B\u043A \u0438\u043D\u0442\u0435\u0440\u0444\u0435\u0439\u0441\u0430",en:"Interface language"},languageAuto:{ru:"\u0410\u0432\u0442\u043E (\u043A\u0430\u043A \u0432 Home Assistant)",en:"Auto (follow Home Assistant)"},interval:{ru:"\u0421\u043A\u043E\u0440\u043E\u0441\u0442\u044C \u043E\u0431\u043D\u043E\u0432\u043B\u0435\u043D\u0438\u044F",en:"Update interval"},intervalLive:{ru:"\u0412 \u0440\u0435\u0430\u043B\u044C\u043D\u043E\u043C \u0432\u0440\u0435\u043C\u0435\u043D\u0438",en:"Real time (default)"},intervalSec:{ru:"{n} \u0441\u0435\u043A",en:"{n} s"},intervalHint:{ru:"\u041A\u0430\u043A \u0447\u0430\u0441\u0442\u043E \u043E\u0431\u043D\u043E\u0432\u043B\u044F\u0442\u044C \u043F\u043E\u043A\u0430\u0437\u0430\u043D\u0438\u044F \u043D\u0430 \u043A\u0430\u0440\u0442\u043E\u0447\u043A\u0435. 0 \u2014 \u043F\u0440\u0438 \u043A\u0430\u0436\u0434\u043E\u043C \u0438\u0437\u043C\u0435\u043D\u0435\u043D\u0438\u0438 \u0441\u043E\u0441\u0442\u043E\u044F\u043D\u0438\u044F \u0432 HA (\u043F\u043E \u0443\u043C\u043E\u043B\u0447\u0430\u043D\u0438\u044E). \u0412\u044B\u0431\u043E\u0440 outbound \u0438 \u043A\u043D\u043E\u043F\u043A\u0438 \u0442\u0435\u0441\u0442\u0430 \u0432\u0441\u0435\u0433\u0434\u0430 \u043F\u0440\u0438\u043C\u0435\u043D\u044F\u044E\u0442\u0441\u044F \u0441\u0440\u0430\u0437\u0443.",en:"How often the card refreshes its values. 0 \u2014 on every HA state change (default). Outbound selection and the test buttons always apply instantly."},showTestAll:{ru:"\u041A\u043D\u043E\u043F\u043A\u0430 \xAB\u041F\u0440\u043E\u0432\u0435\u0440\u0438\u0442\u044C \u0432\u0441\u0435\xBB",en:"\u201CTest all\u201D button"},showTestAllHint:{ru:"\u041C\u0430\u0441\u0441\u043E\u0432\u044B\u0439 url-test \u043F\u043E \u0432\u0441\u0435\u043C \u0433\u0440\u0443\u043F\u043F\u0430\u043C \u0438 outbound \u0432 \u043E\u0434\u0438\u043D \u043A\u043B\u0438\u043A.",en:"Batch url-test of every group and outbound in one tap."},exclude:{ru:"\u0421\u043A\u0440\u044B\u0442\u044C outbound \u0438\u0437 \u043A\u0430\u0440\u0442\u043E\u0447\u043A\u0438",en:"Hide outbounds from the card"},excludeHint:{ru:"\u041E\u0442\u043C\u0435\u0447\u0435\u043D\u043D\u044B\u0435 \u0442\u0435\u0433\u0438 \u043D\u0435 \u043F\u043E\u043A\u0430\u0437\u044B\u0432\u0430\u044E\u0442\u0441\u044F \u0432 \u0433\u0440\u0443\u043F\u043F\u0430\u0445 \u0438 \u0431\u043B\u043E\u043A\u0435 Outbound.",en:"Checked tags are hidden from the groups and the Outbound block."},device:{ru:"device_id (\u043D\u0435\u043E\u0431\u044F\u0437\u0430\u0442\u0435\u043B\u044C\u043D\u043E)",en:"device_id (optional)"},deviceHint:{ru:"\u041F\u0440\u0438\u0432\u044F\u0437\u043A\u0430 \u043A \u043A\u043E\u043D\u043A\u0440\u0435\u0442\u043D\u043E\u043C\u0443 \u0443\u0441\u0442\u0440\u043E\u0439\u0441\u0442\u0432\u0443 sing-box, \u0435\u0441\u043B\u0438 \u0438\u0445 \u043D\u0435\u0441\u043A\u043E\u043B\u044C\u043A\u043E.",en:"Pin to a specific sing-box device when several are configured."},entity:{ru:"entity (\u043D\u0435\u043E\u0431\u044F\u0437\u0430\u0442\u0435\u043B\u044C\u043D\u043E)",en:"entity (optional)"},entityHint:{ru:"\u0410\u043B\u044C\u0442\u0435\u0440\u043D\u0430\u0442\u0438\u0432\u043D\u0430\u044F \u043F\u0440\u0438\u0432\u044F\u0437\u043A\u0430 \u0447\u0435\u0440\u0435\u0437 \u043B\u044E\u0431\u0443\u044E \u0441\u0443\u0449\u043D\u043E\u0441\u0442\u044C ha-singbox.",en:"Alternative pin via any ha-singbox entity."}}};function B(o,t){let e=o&&o.language||"auto";if(e==="ru"||e==="en")return e;let i=t&&(t.language||t.locale&&t.locale.language)||"";return String(i).toLowerCase().startsWith("ru")?"ru":"en"}function It(o){return o.split(".").reduce((t,e)=>t&&t[e],Bt)}function I(o,t,e={}){let i=It(t),s=i&&(i[o]||i.en)||t;return Object.entries(e).reduce((n,[r,a])=>n.split(`{${r}}`).join(String(a)),s)}var qt=[0,1,2,3,5,10,30,60],zt="_group_",et="_ping_",Dt="_clash_mode",jt="GLOBAL",it=class extends m{static properties={hass:{},_config:{state:!0},_candidates:{state:!0}};static styles=k`
        .row {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 4px 0;
        }
        .row ha-switch {
            flex: none;
        }
        .row .label {
            flex: 1;
            font-size: 13px;
            overflow-wrap: anywhere;
        }
        ha-textfield,
        ha-select {
            width: 100%;
        }
        .block {
            margin-top: 12px;
        }
        .block-title {
            font-size: 13px;
            color: var(--secondary-text-color);
        }
        .hint {
            font-size: 11px;
            color: var(--secondary-text-color);
            margin: 2px 0 8px;
        }
        .exclude-tag {
            font-family: var(--paper-font-common-base-code-family, monospace);
        }
    `;setConfig(t){this._config={...t},this._loadCandidates()}firstUpdated(){this._loadCandidates()}updated(t){t.has("hass")&&this._loadCandidates()}_lang(){return B(this._config,this.hass)}_t(t,e={}){return I(this._lang(),t,e)}_update(t,e){this._config={...this._config,[t]:e},this.dispatchEvent(new CustomEvent("config-changed",{detail:{config:this._config},bubbles:!0,composed:!0}))}_onText(t,e){this._update(e,t.target.value)}_onSwitch(t,e){this._update(e,t.target.checked)}_onSelectChange(t,e){t.detail&&"value"in t.detail||this._applySelect(e,t.target&&t.target.value)}_onSelectSelected(t,e){!t.detail||!("value"in t.detail)||this._applySelect(e,t.detail.value)}_applySelect(t,e){e==null||e===""||(t==="update_interval"&&(e=Number(e)),this._update(t,e))}_toggleExclude(t,e){let i=new Set(this._config.exclude_outbounds||[]);e?i.add(t):i.delete(t),this._update("exclude_outbounds",[...i].sort())}async _loadCandidates(){if(!(this._candidates!==void 0||this._loading)&&!(!this.hass||typeof this.hass.callWS!="function")){this._loading=!0;try{let t=await this.hass.callWS({type:"config/entity_registry/list"});this._candidates=this._candidateTags(t||[])}catch{this._candidates=[]}finally{this._loading=!1}}}_candidateTags(t){let e=this._config&&this._config.device_id,i=new Set;for(let s of t){if(s.platform!=="singbox"||e&&s.device_id!==e)continue;let n=s.unique_id||"",r=(s.entity_id||"").split(".")[0];if(r==="sensor"&&n.includes(et)){let a=n.slice(n.lastIndexOf(et)+et.length);a!==jt&&i.add(a)}else if(r==="select"&&n.includes(zt)&&!n.endsWith(Dt)){let a=this.hass.states&&this.hass.states[s.entity_id];(a&&a.attributes&&Array.isArray(a.attributes.options)?a.attributes.options:[]).forEach(l=>i.add(l))}}return[...i].sort((s,n)=>s.localeCompare(n))}_languageOptions(){return[{value:"auto",label:this._t("editor.languageAuto")},{value:"ru",label:"\u0420\u0443\u0441\u0441\u043A\u0438\u0439"},{value:"en",label:"English"}]}_intervalOptions(){return qt.map(t=>({value:String(t),label:this._intervalLabel(t)}))}_intervalLabel(t){return t===0?this._t("editor.intervalLive"):this._t("editor.intervalSec",{n:t})}render(){let t=this._config||{},e=Number(t.update_interval)||0,i=new Set(t.exclude_outbounds||[]),s=this._languageOptions(),n=this._intervalOptions(),r=(this._candidates||[]).length>0;return p`
            <ha-textfield
                label=${this._t("editor.title")}
                value=${t.title||"Sing-box"}
                @change=${a=>this._onText(a,"title")}
            ></ha-textfield>

            <div class="block">
                <ha-select
                    label=${this._t("editor.language")}
                    .value=${t.language||"auto"}
                    .options=${s}
                    @change=${a=>this._onSelectChange(a,"language")}
                    @selected=${a=>this._onSelectSelected(a,"language")}
                >
                    ${s.map(a=>p`
                            <mwc-list-item value=${a.value}>
                                ${a.label}
                            </mwc-list-item>
                        `)}
                </ha-select>
            </div>

            <div class="block">
                <ha-select
                    label=${this._t("editor.interval")}
                    .value=${String(e)}
                    .options=${n}
                    @change=${a=>this._onSelectChange(a,"update_interval")}
                    @selected=${a=>this._onSelectSelected(a,"update_interval")}
                >
                    ${n.map(a=>p`
                            <mwc-list-item value=${a.value}>
                                ${a.label}
                            </mwc-list-item>
                        `)}
                </ha-select>
                <div class="hint">${this._t("editor.intervalHint")}</div>
            </div>

            <div class="row block">
                <span class="label">${this._t("editor.showTestAll")}</span>
                <ha-switch
                    .checked=${t.show_test_all!==!1}
                    @change=${a=>this._onSwitch(a,"show_test_all")}
                ></ha-switch>
            </div>
            <div class="hint">${this._t("editor.showTestAllHint")}</div>

            ${r?p`
                      <div class="block">
                          <div class="block-title">
                              ${this._t("editor.exclude")}
                          </div>
                          <div class="hint">${this._t("editor.excludeHint")}</div>
                          ${this._candidates.map(a=>p`
                                  <div class="row exclude-row">
                                      <span class="label exclude-tag"
                                          >${a}</span
                                      >
                                      <ha-switch
                                          .checked=${i.has(a)}
                                          @change=${d=>this._toggleExclude(a,d.target.checked)}
                                      ></ha-switch>
                                  </div>
                              `)}
                      </div>
                  `:p`
                      <ha-textfield
                          label=${this._t("editor.exclude")}
                          value=${(t.exclude_outbounds||[]).join(", ")}
                          @change=${a=>this._update("exclude_outbounds",a.target.value.split(",").map(d=>d.trim()).filter(Boolean))}
                      ></ha-textfield>
                      <div class="hint">${this._t("editor.excludeHint")}</div>
                  `}

            <ha-textfield
                label=${this._t("editor.device")}
                value=${t.device_id||""}
                @change=${a=>this._onText(a,"device_id")}
            ></ha-textfield>
            <div class="hint">${this._t("editor.deviceHint")}</div>

            <ha-textfield
                label=${this._t("editor.entity")}
                value=${t.entity||""}
                @change=${a=>this._onText(a,"entity")}
            ></ha-textfield>
            <div class="hint">${this._t("editor.entityHint")}</div>
        `}};customElements.define("singbox-panel-card-editor",it);var Gt="0.1.15",q="_group_",z="_ping_",st="_clash_mode",Ft="GLOBAL",Wt=1e4,wt="Sing-box",nt=class extends m{static properties={_state:{state:!0},_model:{state:!0},_testing:{state:!0},_testingAll:{state:!0}};static styles=At;constructor(){super(),this._hass=null,this._config={},this._discovered=!1,this._state="loading",this._model=null,this._testing={},this._testingAll=!1,this._fallbackNote=null,this._error=null,this._lastRenderAt=0,this._renderTimer=null,this._pendingSelections={}}static getStubConfig(){return{title:wt,show_test_all:!0,exclude_outbounds:[],update_interval:0,language:"auto"}}static getConfigElement(){return document.createElement("singbox-panel-card-editor")}setConfig(t){if(!t||typeof t!="object")throw new Error("Invalid configuration");let e=this._config||{},i={title:wt,show_test_all:!0,exclude_outbounds:[],update_interval:0,language:"auto",...t};i.exclude_outbounds=(Array.isArray(i.exclude_outbounds)?i.exclude_outbounds:String(i.exclude_outbounds??"").split(",")).map(n=>String(n).trim()).filter(Boolean);let s=Number(i.update_interval);i.update_interval=Number.isFinite(s)&&s>0?Math.min(s,3600):0,this._config=i,this._discovered&&this._needsRediscovery(e,i)&&(this._discovered=!1,this._hass&&this._discover()),this.requestUpdate()}_needsRediscovery(t,e){if(t.device_id!==e.device_id||t.entity!==e.entity)return!0;let i=t.exclude_outbounds||[],s=e.exclude_outbounds||[];return i.length!==s.length||s.some(n=>!i.includes(n))}getCardSize(){return 4}get hass(){return this._hass}set hass(t){this._hass=t,t&&!this._discovered&&(this._discovered=!0,this._discover()),t&&this._scheduleRender()}_lang(){return B(this._config,this._hass)}_t(t,e={}){return I(this._lang(),t,e)}async _discover(){this._state="loading",this._fallbackNote=null;try{let t=await this._hass.callWS({type:"config/entity_registry/list"});if(!Array.isArray(t))throw new Error("registry is unavailable");let e=n=>this._domain(n)==="select"&&n.unique_id&&n.unique_id.includes(q)&&!n.unique_id.endsWith(st),i=n=>n.filter(e),s=t;if(this._config.device_id){let n=t.filter(r=>r.device_id===this._config.device_id);i(n).length>0?s=n:this._fallbackNote={key:"fallback.device",params:{device:this._config.device_id,count:n.length}}}else if(this._config.entity){let n=t.find(r=>r.entity_id===this._config.entity);if(!n)this._fallbackNote={key:"fallback.entityNotFound",params:{entity:this._config.entity}};else{let r=t.filter(a=>n.config_entry_id&&a.config_entry_id===n.config_entry_id||n.device_id&&a.device_id===n.device_id);i(r).length>0?s=r:this._fallbackNote={key:"fallback.entityNoGroups",params:{entity:this._config.entity}}}}if(this._model=this._buildModel(s),this._model.groups.length===0){let n=t.filter(h=>this._domain(h)==="select"),r=i(t),a=t.filter(h=>this._domain(h)==="sensor"&&h.unique_id&&h.unique_id.includes(z)),d=this._config.device_id?t.filter(h=>h.device_id===this._config.device_id).length:null,l=this._config.device_id?t.filter(h=>h.device_id===this._config.device_id):[],u=l.slice(0,5).map(h=>{let g=h.unique_id?h.unique_id.slice(0,40):"\u2014";return`${h.entity_id} (${this._domain(h)}) [${g}]`}).join(", ");l.length&&console.warn("singbox-panel: records matched by pin:",l.map(h=>`${h.entity_id} ${this._domain(h)} ${h.unique_id??""}`).join(`
`));let c=r.slice(0,5).map(h=>`${h.entity_id} [${h.unique_id}]`).join(", ");this._state="error",r.length===0&&d!==null?this._error={key:"errors.groupsDevice",params:{count:d,selects:n.length,pings:a.length,sample:u}}:r.length===0?this._error={key:"errors.groupsNone",params:{selects:n.length,pings:a.length}}:this._error={key:"errors.groupsBadUid",params:{sample:c}};return}this._fallbackNote&&console.warn(`singbox-panel: ${this._t(this._fallbackNote.key,this._fallbackNote.params)}`),this._state="ready"}catch(t){this._state="error",this._error={key:"errors.loadFailed",params:{msg:t&&t.message?t.message:String(t)}}}}_buildModel(t){let e=new Set(this._config.exclude_outbounds||[]),i={};for(let l of t)if(this._domain(l)==="sensor"&&l.unique_id&&l.unique_id.includes(z)){let u=l.unique_id.slice(l.unique_id.lastIndexOf(z)+z.length);if(u===Ft)continue;i[u]=l.entity_id}let s=[],n=new Set;for(let l of t){if(this._domain(l)!=="select"||!l.unique_id||!l.unique_id.includes(q)||l.unique_id.endsWith(st))continue;let u=l.unique_id.slice(l.unique_id.lastIndexOf(q)+q.length),c=this._hass.states[l.entity_id],h=c&&c.attributes&&Array.isArray(c.attributes.options)?c.attributes.options:[];h.forEach(f=>n.add(f));let g=h.filter(f=>!e.has(f)).map(f=>({tag:f,pingEntity:i[f]||null}));g.length!==0&&s.push({tag:u,entityId:l.entity_id,options:g})}let r=Object.keys(i).filter(l=>!n.has(l)&&!e.has(l)).sort().map(l=>({tag:l,pingEntity:i[l]})),a=l=>{let u=t.find(c=>this._domain(c)==="sensor"&&c.unique_id&&c.unique_id.endsWith(l));return u?u.entity_id:null},d=t.find(l=>this._domain(l)==="select"&&l.unique_id&&l.unique_id.endsWith(st));return{version:a("_version"),uplink:a("_uplink"),downlink:a("_downlink"),uplinkTotal:a("_uplink_total"),downlinkTotal:a("_downlink_total"),memory:a("_memory"),connectionsIn:a("_connections_in"),clashMode:d?d.entity_id:null,groups:s,standalone:r}}_entity(t){return t?this._hass.states[t]:void 0}_domain(t){return t.entity_id?t.entity_id.split(".")[0]:t.domain||""}_stateValue(t){let e=this._entity(t);return e?e.state==="unavailable"?null:e.state:null}_formatSpeed(t){let e=this._entity(t);if(!e||e.state==="unavailable"||e.state==="unknown")return{value:"\u2014",unit:""};let i=Number(e.state);return Number.isFinite(i)?{value:i.toLocaleString(void 0,{maximumFractionDigits:1}),unit:e.attributes&&e.attributes.unit_of_measurement?e.attributes.unit_of_measurement:""}:{value:"\u2014",unit:""}}_formatBytes(t){let e=this._entity(t);if(!e||e.state==="unavailable"||e.state==="unknown")return"\u2014";let i=Number(e.state);if(!Number.isFinite(i))return"\u2014";let s=e.attributes&&e.attributes.unit_of_measurement||"B",n={B:1,kB:1e3,MB:1e6,GB:1e9,TB:1e12,KiB:1024,MiB:1024**2,GiB:1024**3,TiB:1024**4},r=i*(n[s]||1),a=["B","KiB","MiB","GiB","TiB"],d=r,l=0;for(;d>=1024&&l<a.length-1;)d/=1024,l+=1;let u=l?1:0;return`${d.toLocaleString(void 0,{maximumFractionDigits:u})} ${a[l]}`}_ping(t){let e=this._entity(t.pingEntity);if(!e||e.state==="unavailable"||e.state==="unknown")return null;let i=Number(e.state);return Number.isFinite(i)?i:null}_pingClass(t){return t===null?"none":t<=100?"good":t<=300?"warn":"bad"}_pingText(t){return t===null?"\u2014":`${t} ms`}_refreshMs(){let t=Number(this._config.update_interval)||0;return Math.min(Math.max(t,0),3600)*1e3}_scheduleRender(t=!1){if(!this._hass)return;let e=this._refreshMs();if(e<=0||t){this._requestRender();return}let i=Date.now(),s=this._lastRenderAt+e;if(i>=s){this._requestRender();return}this._renderTimer||(this._renderTimer=setTimeout(()=>{this._renderTimer=null,this._requestRender()},s-i))}_requestRender(){this._renderTimer&&(clearTimeout(this._renderTimer),this._renderTimer=null),this.requestUpdate()}_groupCurrent(t){let e=this._entity(t.entityId),i=e&&e.state!=="unavailable"?e.state:null,s=this._pendingSelections[t.entityId];return s?s.tag===i||Date.now()-s.ts>Wt?(delete this._pendingSelections[t.entityId],i):s.tag:i}async _callService(t,e,i,s){try{await this._hass.callService(t,e,s?{...i,entity_id:s}:i)}catch(n){let r=String(n&&n.message?n.message:n);if(s&&/extra keys not allowed/.test(r)){await this._hass.callService(t,e,i);return}throw n}}async _selectNode(t,e,i){if(!(!this._hass||!i)){this._pendingSelections[i]={tag:e,ts:Date.now()},this._scheduleRender(!0);try{await this._callService("singbox","select_outbound",{group_tag:t,outbound_tag:e},i)}catch(s){console.error("singbox-panel: select_outbound failed",s),delete this._pendingSelections[i]}this._scheduleRender(!0)}}async _testGroup(t){let e=t.options||[];if(!this._hass||this._testing[t.tag]||e.length===0)return;let i=Object.fromEntries(e.map(s=>[s.tag,!0]));this._testing={...this._testing,[t.tag]:!0,...i};try{await Promise.all(e.map(s=>this._callService("singbox","url_test",{outbound_tag:s.tag},s.pingEntity||t.entityId).catch(n=>{console.error(`singbox-panel: url_test failed for ${s.tag}`,n)})))}finally{setTimeout(()=>{let s={...this._testing};delete s[t.tag];for(let n of e)delete s[n.tag];this._testing=s},4e3)}}async _pingNode(t,e){if(!(!this._hass||this._testing[t])){this._testing={...this._testing,[t]:!0};try{await this._callService("singbox","url_test",{outbound_tag:t},e)}catch(i){console.error("singbox-panel: url_test failed",i)}finally{setTimeout(()=>{this._testing={...this._testing,[t]:!1}},4e3)}}}async _testAll(){if(!this._hass||!this._model||this._testingAll)return;this._testingAll=!0;let t=new Set,e=[];for(let i of this._model.groups)for(let s of i.options)t.has(s.tag)||(t.add(s.tag),e.push({tag:s.tag,target:s.pingEntity||i.entityId}));for(let i of this._model.standalone)t.has(i.tag)||(t.add(i.tag),e.push({tag:i.tag,target:i.pingEntity}));try{await Promise.all(e.map(i=>this._callService("singbox","url_test",{outbound_tag:i.tag},i.target).catch(s=>{console.error(`singbox-panel: url_test failed for ${i.tag}`,s)})))}finally{setTimeout(()=>{this._testingAll=!1},4e3)}}render(){if(this._lastRenderAt=Date.now(),this._state==="error"){let n=this._error||{key:"errors.loadFailed",params:{}};return p`
                <div class="card">
                    <div class="state-msg">
                        ${this._t(n.key,n.params)}
                    </div>
                </div>
            `}if(this._state==="loading"||!this._model)return p`
                <div class="card">
                    <div class="state-msg">
                        <div class="spinner"></div>
                        <span>${this._t("loading")}</span>
                    </div>
                </div>
            `;let t=this._model,e=this._stateValue(t.version),i=this._stateValue(t.clashMode),s=this._config.show_test_all!==!1&&(t.groups.length>0||t.standalone.length>0);return p`
            <div class="card">
                <div class="header">
                    <h2>${this._config.title}</h2>
                    <div class="meta">
                        ${e?p`<span>${e}</span>`:""}
                        ${i?p`<span> · ${i}</span>`:""}
                    </div>
                    ${s?p`
                              <button
                                  class="test-all-btn"
                                  ?disabled=${this._testingAll}
                                  @click=${()=>this._testAll()}
                              >
                                  <ha-icon icon="mdi:flash-outline"></ha-icon>
                                  ${this._testingAll?this._t("testing"):this._t("testAll")}
                              </button>
                          `:""}
                </div>

                <div class="speeds">
                    ${this._speedTile("up","mdi:arrow-up-bold",this._t("speedUp"),t.uplink)}
                    ${this._speedTile("down","mdi:arrow-down-bold",this._t("speedDown"),t.downlink)}
                </div>

                <div class="totals">
                    ${this._totalChip("mdi:arrow-up",this._formatBytes(t.uplinkTotal))}
                    ${this._totalChip("mdi:arrow-down",this._formatBytes(t.downlinkTotal))}
                    ${this._totalChip("mdi:memory",this._formatBytes(t.memory))}
                    ${this._totalChip("mdi:lan-connect",this._stateValue(t.connectionsIn))}
                </div>

                ${t.groups.map(n=>this._renderGroup(n))}
                ${t.standalone.length?this._renderStandalone(t.standalone):""}

                ${this._fallbackNote?p`<div class="fallback-note">${this._t(this._fallbackNote.key,this._fallbackNote.params)}</div>`:""}
                <div class="footer">sing-box panel · v${Gt}</div>
            </div>
        `}_renderStandalone(t){return p`
            <div class="group">
                <div class="group-head">
                    <span class="group-name">Outbound</span>
                </div>
                <div class="nodes">
                    ${t.map(e=>this._renderStandaloneNode(e))}
                </div>
            </div>
        `}_renderStandaloneNode(t){let e=this._ping(t),i=!!this._testing[t.tag];return p`
            <div class="node">
                <span class="node-name standalone">${t.tag}</span>
                ${e!==null?p`<span class="ping ${this._pingClass(e)}">${this._pingText(e)}</span>`:""}
                <button
                    class="node-ping"
                    title=${this._t("pingTitle",{tag:t.tag})}
                    ?disabled=${i}
                    @click=${()=>this._pingNode(t.tag,t.pingEntity)}
                >
                    <ha-icon icon="mdi:radar"></ha-icon>
                </button>
            </div>
        `}_speedTile(t,e,i,s){let{value:n,unit:r}=this._formatSpeed(s);return p`
            <div class="tile ${t}">
                <ha-icon icon=${e}></ha-icon>
                <div class="tile-body">
                    <div class="tile-label">${i}</div>
                    <div class="tile-value">${n}<span class="unit">${r}</span></div>
                </div>
            </div>
        `}_totalChip(t,e){return p`
            <span class="chip-stat">
                <ha-icon icon=${t}></ha-icon>
                <b>${e}</b>
            </span>
        `}_renderGroup(t){let e=this._groupCurrent(t),i=!!this._testing[t.tag];return p`
            <div class="group">
                <div class="group-head">
                    <span class="group-name">${t.tag}</span>
                    <span class="group-current">
                        ${e?p`→ <b>${e}</b>`:""}
                    </span>
                    <button
                        class="test-btn"
                        ?disabled=${i}
                        @click=${()=>this._testGroup(t)}
                    >
                        <ha-icon icon="mdi:flash-outline"></ha-icon>
                        ${i?this._t("testing"):this._t("test")}
                    </button>
                </div>
                <div class="nodes">
                    ${t.options.map(s=>this._renderNode(t,s,e))}
                </div>
            </div>
        `}_renderNode(t,e,i){let s=this._ping(e),n=e.tag===i,r=!!this._testing[e.tag];return p`
            <div class="node ${n?"active":""}">
                <button
                    class="node-select"
                    title=${this._t("selectTitle",{tag:e.tag})}
                    @click=${()=>this._selectNode(t.tag,e.tag,t.entityId)}
                >
                    <span class="node-name">${e.tag}</span>
                    ${s!==null?p`<span class="ping ${this._pingClass(s)}">${this._pingText(s)}</span>`:""}
                </button>
                <button
                    class="node-ping"
                    title=${this._t("pingTitle",{tag:e.tag})}
                    ?disabled=${r}
                    @click=${()=>this._pingNode(e.tag,e.pingEntity||t.entityId)}
                >
                    <ha-icon icon="mdi:radar"></ha-icon>
                </button>
            </div>
        `}};customElements.define("singbox-panel-card",nt);window.customCards=window.customCards||[];window.customCards.push({type:"singbox-panel-card",name:"Sing-box Panel",description:"\u041F\u0430\u043D\u0435\u043B\u044C \u043C\u043E\u043D\u0438\u0442\u043E\u0440\u0438\u043D\u0433\u0430 \u0438 \u0443\u043F\u0440\u0430\u0432\u043B\u0435\u043D\u0438\u044F \u043F\u0440\u043E\u043A\u0441\u0438 sing-box",preview:!1});
/*! Bundled license information:

@lit/reactive-element/css-tag.js:
  (**
   * @license
   * Copyright 2019 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

@lit/reactive-element/reactive-element.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

lit-html/lit-html.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

lit-element/lit-element.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

lit-html/is-server.js:
  (**
   * @license
   * Copyright 2022 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)
*/
