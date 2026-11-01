var z=globalThis,B=z.ShadowRoot&&(z.ShadyCSS===void 0||z.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,V=Symbol(),ut=new WeakMap,C=class{constructor(t,e,n){if(this._$cssResult$=!0,n!==V)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o,e=this.t;if(B&&t===void 0){let n=e!==void 0&&e.length===1;n&&(t=ut.get(e)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),n&&ut.set(e,t))}return t}toString(){return this.cssText}},pt=o=>new C(typeof o=="string"?o:o+"",void 0,V),E=(o,...t)=>{let e=o.length===1?o[0]:t.reduce((n,i,s)=>n+(r=>{if(r._$cssResult$===!0)return r.cssText;if(typeof r=="number")return r;throw Error("Value passed to 'css' function must be a 'css' function result: "+r+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+o[s+1],o[0]);return new C(e,o,V)},_t=(o,t)=>{if(B)o.adoptedStyleSheets=t.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(let e of t){let n=document.createElement("style"),i=z.litNonce;i!==void 0&&n.setAttribute("nonce",i),n.textContent=e.cssText,o.appendChild(n)}},K=B?o=>o:o=>o instanceof CSSStyleSheet?(t=>{let e="";for(let n of t.cssRules)e+=n.cssText;return pt(e)})(o):o;var{is:Bt,defineProperty:It,getOwnPropertyDescriptor:qt,getOwnPropertyNames:Dt,getOwnPropertySymbols:Ft,getPrototypeOf:jt}=Object,I=globalThis,gt=I.trustedTypes,Gt=gt?gt.emptyScript:"",Wt=I.reactiveElementPolyfillSupport,T=(o,t)=>o,X={toAttribute(o,t){switch(t){case Boolean:o=o?Gt:null;break;case Object:case Array:o=o==null?o:JSON.stringify(o)}return o},fromAttribute(o,t){let e=o;switch(t){case Boolean:e=o!==null;break;case Number:e=o===null?null:Number(o);break;case Object:case Array:try{e=JSON.parse(o)}catch{e=null}}return e}},mt=(o,t)=>!Bt(o,t),ft={attribute:!0,type:String,converter:X,reflect:!1,useDefault:!1,hasChanged:mt};Symbol.metadata??=Symbol("metadata"),I.litPropertyMetadata??=new WeakMap;var v=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=ft){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){let n=Symbol(),i=this.getPropertyDescriptor(t,n,e);i!==void 0&&It(this.prototype,t,i)}}static getPropertyDescriptor(t,e,n){let{get:i,set:s}=qt(this.prototype,t)??{get(){return this[e]},set(r){this[e]=r}};return{get:i,set(r){let a=i?.call(this);s?.call(this,r),this.requestUpdate(t,a,n)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??ft}static _$Ei(){if(this.hasOwnProperty(T("elementProperties")))return;let t=jt(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(T("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(T("properties"))){let e=this.properties,n=[...Dt(e),...Ft(e)];for(let i of n)this.createProperty(i,e[i])}let t=this[Symbol.metadata];if(t!==null){let e=litPropertyMetadata.get(t);if(e!==void 0)for(let[n,i]of e)this.elementProperties.set(n,i)}this._$Eh=new Map;for(let[e,n]of this.elementProperties){let i=this._$Eu(e,n);i!==void 0&&this._$Eh.set(i,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){let e=[];if(Array.isArray(t)){let n=new Set(t.flat(1/0).reverse());for(let i of n)e.unshift(K(i))}else t!==void 0&&e.push(K(t));return e}static _$Eu(t,e){let n=e.attribute;return n===!1?void 0:typeof n=="string"?n:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),this.renderRoot!==void 0&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){let t=new Map,e=this.constructor.elementProperties;for(let n of e.keys())this.hasOwnProperty(n)&&(t.set(n,this[n]),delete this[n]);t.size>0&&(this._$Ep=t)}createRenderRoot(){let t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return _t(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,n){this._$AK(t,n)}_$ET(t,e){let n=this.constructor.elementProperties.get(t),i=this.constructor._$Eu(t,n);if(i!==void 0&&n.reflect===!0){let s=(n.converter?.toAttribute!==void 0?n.converter:X).toAttribute(e,n.type);this._$Em=t,s==null?this.removeAttribute(i):this.setAttribute(i,s),this._$Em=null}}_$AK(t,e){let n=this.constructor,i=n._$Eh.get(t);if(i!==void 0&&this._$Em!==i){let s=n.getPropertyOptions(i),r=typeof s.converter=="function"?{fromAttribute:s.converter}:s.converter?.fromAttribute!==void 0?s.converter:X;this._$Em=i;let a=r.fromAttribute(e,s.type);this[i]=a??this._$Ej?.get(i)??a,this._$Em=null}}requestUpdate(t,e,n,i=!1,s){if(t!==void 0){let r=this.constructor;if(i===!1&&(s=this[t]),n??=r.getPropertyOptions(t),!((n.hasChanged??mt)(s,e)||n.useDefault&&n.reflect&&s===this._$Ej?.get(t)&&!this.hasAttribute(r._$Eu(t,n))))return;this.C(t,e,n)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(t,e,{useDefault:n,reflect:i,wrapped:s},r){n&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,r??e??this[t]),s!==!0||r!==void 0)||(this._$AL.has(t)||(this.hasUpdated||n||(e=void 0),this._$AL.set(t,e)),i===!0&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}let t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[i,s]of this._$Ep)this[i]=s;this._$Ep=void 0}let n=this.constructor.elementProperties;if(n.size>0)for(let[i,s]of n){let{wrapped:r}=s,a=this[i];r!==!0||this._$AL.has(i)||a===void 0||this.C(i,void 0,s,a)}}let t=!1,e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(n=>n.hostUpdate?.()),this.update(e)):this._$EM()}catch(n){throw t=!1,this._$EM(),n}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(t){}firstUpdated(t){}};v.elementStyles=[],v.shadowRootOptions={mode:"open"},v[T("elementProperties")]=new Map,v[T("finalized")]=new Map,Wt?.({ReactiveElement:v}),(I.reactiveElementVersions??=[]).push("2.1.2");var nt=globalThis,vt=o=>o,q=nt.trustedTypes,bt=q?q.createPolicy("lit-html",{createHTML:o=>o}):void 0,At="$lit$",b=`lit$${Math.random().toFixed(9).slice(2)}$`,kt="?"+b,Vt=`<${kt}>`,$=document,P=()=>$.createComment(""),M=o=>o===null||typeof o!="object"&&typeof o!="function",it=Array.isArray,Kt=o=>it(o)||typeof o?.[Symbol.iterator]=="function",J=`[ 	
\f\r]`,N=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,xt=/-->/g,yt=/>/g,x=RegExp(`>|${J}(?:([^\\s"'>=/]+)(${J}*=${J}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),$t=/'/g,wt=/"/g,Ct=/^(?:script|style|textarea|title)$/i,st=o=>(t,...e)=>({_$litType$:o,strings:t,values:e}),p=st(1),k=st(2),_e=st(3),w=Symbol.for("lit-noChange"),g=Symbol.for("lit-nothing"),St=new WeakMap,y=$.createTreeWalker($,129);function Et(o,t){if(!it(o)||!o.hasOwnProperty("raw"))throw Error("invalid template strings array");return bt!==void 0?bt.createHTML(t):t}var Xt=(o,t)=>{let e=o.length-1,n=[],i,s=t===2?"<svg>":t===3?"<math>":"",r=N;for(let a=0;a<e;a++){let c=o[a],l,d,h=-1,_=0;for(;_<c.length&&(r.lastIndex=_,d=r.exec(c),d!==null);)_=r.lastIndex,r===N?d[1]==="!--"?r=xt:d[1]!==void 0?r=yt:d[2]!==void 0?(Ct.test(d[2])&&(i=RegExp("</"+d[2],"g")),r=x):d[3]!==void 0&&(r=x):r===x?d[0]===">"?(r=i??N,h=-1):d[1]===void 0?h=-2:(h=r.lastIndex-d[2].length,l=d[1],r=d[3]===void 0?x:d[3]==='"'?wt:$t):r===wt||r===$t?r=x:r===xt||r===yt?r=N:(r=x,i=void 0);let f=r===x&&o[a+1].startsWith("/>")?" ":"";s+=r===N?c+Vt:h>=0?(n.push(l),c.slice(0,h)+At+c.slice(h)+b+f):c+b+(h===-2?a:f)}return[Et(o,s+(o[e]||"<?>")+(t===2?"</svg>":t===3?"</math>":"")),n]},O=class o{constructor({strings:t,_$litType$:e},n){let i;this.parts=[];let s=0,r=0,a=t.length-1,c=this.parts,[l,d]=Xt(t,e);if(this.el=o.createElement(l,n),y.currentNode=this.el.content,e===2||e===3){let h=this.el.content.firstChild;h.replaceWith(...h.childNodes)}for(;(i=y.nextNode())!==null&&c.length<a;){if(i.nodeType===1){if(i.hasAttributes())for(let h of i.getAttributeNames())if(h.endsWith(At)){let _=d[r++],f=i.getAttribute(h).split(b),u=/([.?@])?(.*)/.exec(_);c.push({type:1,index:s,name:u[2],strings:f,ctor:u[1]==="."?Z:u[1]==="?"?Q:u[1]==="@"?tt:A}),i.removeAttribute(h)}else h.startsWith(b)&&(c.push({type:6,index:s}),i.removeAttribute(h));if(Ct.test(i.tagName)){let h=i.textContent.split(b),_=h.length-1;if(_>0){i.textContent=q?q.emptyScript:"";for(let f=0;f<_;f++)i.append(h[f],P()),y.nextNode(),c.push({type:2,index:++s});i.append(h[_],P())}}}else if(i.nodeType===8)if(i.data===kt)c.push({type:2,index:s});else{let h=-1;for(;(h=i.data.indexOf(b,h+1))!==-1;)c.push({type:7,index:s}),h+=b.length-1}s++}}static createElement(t,e){let n=$.createElement("template");return n.innerHTML=t,n}};function S(o,t,e=o,n){if(t===w)return t;let i=n!==void 0?e._$Co?.[n]:e._$Cl,s=M(t)?void 0:t._$litDirective$;return i?.constructor!==s&&(i?._$AO?.(!1),s===void 0?i=void 0:(i=new s(o),i._$AT(o,e,n)),n!==void 0?(e._$Co??=[])[n]=i:e._$Cl=i),i!==void 0&&(t=S(o,i._$AS(o,t.values),i,n)),t}var Y=class{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){let{el:{content:e},parts:n}=this._$AD,i=(t?.creationScope??$).importNode(e,!0);y.currentNode=i;let s=y.nextNode(),r=0,a=0,c=n[0];for(;c!==void 0;){if(r===c.index){let l;c.type===2?l=new R(s,s.nextSibling,this,t):c.type===1?l=new c.ctor(s,c.name,c.strings,this,t):c.type===6&&(l=new et(s,this,t)),this._$AV.push(l),c=n[++a]}r!==c?.index&&(s=y.nextNode(),r++)}return y.currentNode=$,i}p(t){let e=0;for(let n of this._$AV)n!==void 0&&(n.strings!==void 0?(n._$AI(t,n,e),e+=n.strings.length-2):n._$AI(t[e])),e++}},R=class o{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,n,i){this.type=2,this._$AH=g,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=n,this.options=i,this._$Cv=i?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode,e=this._$AM;return e!==void 0&&t?.nodeType===11&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=S(this,t,e),M(t)?t===g||t==null||t===""?(this._$AH!==g&&this._$AR(),this._$AH=g):t!==this._$AH&&t!==w&&this._(t):t._$litType$!==void 0?this.$(t):t.nodeType!==void 0?this.T(t):Kt(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==g&&M(this._$AH)?this._$AA.nextSibling.data=t:this.T($.createTextNode(t)),this._$AH=t}$(t){let{values:e,_$litType$:n}=t,i=typeof n=="number"?this._$AC(t):(n.el===void 0&&(n.el=O.createElement(Et(n.h,n.h[0]),this.options)),n);if(this._$AH?._$AD===i)this._$AH.p(e);else{let s=new Y(i,this),r=s.u(this.options);s.p(e),this.T(r),this._$AH=s}}_$AC(t){let e=St.get(t.strings);return e===void 0&&St.set(t.strings,e=new O(t)),e}k(t){it(this._$AH)||(this._$AH=[],this._$AR());let e=this._$AH,n,i=0;for(let s of t)i===e.length?e.push(n=new o(this.O(P()),this.O(P()),this,this.options)):n=e[i],n._$AI(s),i++;i<e.length&&(this._$AR(n&&n._$AB.nextSibling,i),e.length=i)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){let n=vt(t).nextSibling;vt(t).remove(),t=n}}setConnected(t){this._$AM===void 0&&(this._$Cv=t,this._$AP?.(t))}},A=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,n,i,s){this.type=1,this._$AH=g,this._$AN=void 0,this.element=t,this.name=e,this._$AM=i,this.options=s,n.length>2||n[0]!==""||n[1]!==""?(this._$AH=Array(n.length-1).fill(new String),this.strings=n):this._$AH=g}_$AI(t,e=this,n,i){let s=this.strings,r=!1;if(s===void 0)t=S(this,t,e,0),r=!M(t)||t!==this._$AH&&t!==w,r&&(this._$AH=t);else{let a=t,c,l;for(t=s[0],c=0;c<s.length-1;c++)l=S(this,a[n+c],e,c),l===w&&(l=this._$AH[c]),r||=!M(l)||l!==this._$AH[c],l===g?t=g:t!==g&&(t+=(l??"")+s[c+1]),this._$AH[c]=l}r&&!i&&this.j(t)}j(t){t===g?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}},Z=class extends A{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===g?void 0:t}},Q=class extends A{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==g)}},tt=class extends A{constructor(t,e,n,i,s){super(t,e,n,i,s),this.type=5}_$AI(t,e=this){if((t=S(this,t,e,0)??g)===w)return;let n=this._$AH,i=t===g&&n!==g||t.capture!==n.capture||t.once!==n.once||t.passive!==n.passive,s=t!==g&&(n===g||i);i&&this.element.removeEventListener(this.name,this,n),s&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}},et=class{constructor(t,e,n){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=n}get _$AU(){return this._$AM._$AU}_$AI(t){S(this,t)}};var Jt=nt.litHtmlPolyfillSupport;Jt?.(O,R),(nt.litHtmlVersions??=[]).push("3.3.3");var Tt=(o,t,e)=>{let n=e?.renderBefore??t,i=n._$litPart$;if(i===void 0){let s=e?.renderBefore??null;n._$litPart$=i=new R(t.insertBefore(P(),s),s,void 0,e??{})}return i._$AI(o),i};var ot=globalThis,m=class extends v{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){let e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=Tt(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return w}};m._$litElement$=!0,m.finalized=!0,ot.litElementHydrateSupport?.({LitElement:m});var Yt=ot.litElementPolyfillSupport;Yt?.({LitElement:m});(ot.litElementVersions??=[]).push("4.2.2");var Nt=E`
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

    /* ---------- traffic chart ---------- */
    .chart {
        margin-top: 4px;
        margin-bottom: 14px;
    }
    .chart-head {
        display: flex;
        align-items: baseline;
        gap: 10px;
        margin-bottom: 6px;
        font-size: 12px;
        color: var(--secondary-text-color);
    }
    .chart-peak {
        font-variant-numeric: tabular-nums;
    }
    .chart-scale {
        margin-left: auto;
        font-variant-numeric: tabular-nums;
        font-size: 11px;
        opacity: 0.75;
    }
    .chart-legend {
        margin-left: auto;
        display: inline-flex;
        gap: 12px;
        font-size: 11px;
        color: var(--secondary-text-color);
    }
    .chart-legend .legend-item {
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .chart-legend .legend-item i {
        width: 8px;
        height: 8px;
        border-radius: 2px;
        display: inline-block;
    }
    .chart-legend .legend-item.up i { background: #ff7043; }
    .chart-legend .legend-item.down i { background: var(--success-color, #2e7d32); }
    .chart-svg {
        display: block;
        width: 100%;
        height: 96px;
        overflow: visible;
    }
    .chart-grid {
        stroke: var(--divider-color, rgba(0, 0, 0, 0.12));
        stroke-width: 1;
    }
    .chart-line {
        fill: none;
        stroke-width: 1.6;
        stroke-linejoin: round;
        stroke-linecap: round;
    }
    .chart-line.up { stroke: #ff7043; }
    .chart-line.down { stroke: var(--success-color, #2e7d32); }
    .chart-fill { stroke: none; }
    /* The two series overlap, so keep the areas translucent and let the
       stroked lines carry the shape. */
    .chart-fill.up { fill: color-mix(in srgb, #ff7043 14%, transparent); }
    .chart-fill.down {
        fill: color-mix(in srgb, var(--success-color, #2e7d32) 14%, transparent);
    }
    .chart-empty {
        margin-top: -58px;
        text-align: center;
        font-size: 12px;
        color: var(--disabled-text-color);
        pointer-events: none;
    }

    /* ---------- connections ---------- */
    .connections {
        margin-top: 14px;
        border-top: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
        padding-top: 12px;
    }
    .conn-head {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 10px;
    }
    .conn-title {
        font-size: 14px;
        font-weight: 600;
        color: var(--primary-text-color);
    }
    .conn-count {
        font-size: 12px;
        color: var(--secondary-text-color);
        font-variant-numeric: tabular-nums;
    }
    .conn-close-all {
        margin-left: auto;
        flex: none;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border: none;
        border-radius: 8px;
        padding: 5px 8px;
        cursor: pointer;
        color: var(--secondary-text-color);
        background: var(--secondary-background-color, rgba(0, 0, 0, 0.05));
        transition: background 0.15s ease, color 0.15s ease;
    }
    .conn-close-all:hover {
        background: var(--error-color, #c62828);
        color: var(--text-primary-color, #fff);
    }
    .conn-close-all[disabled] {
        opacity: 0.5;
        cursor: default;
        pointer-events: none;
    }
    .conn-close-all ha-icon { --mdc-icon-size: 16px; }
    .conn-filters {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-bottom: 10px;
    }
    .conn-search {
        flex: 1 1 160px;
        min-width: 0;
        border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
        border-radius: 8px;
        padding: 6px 9px;
        font-size: 12px;
        font-family: inherit;
        color: var(--primary-text-color);
        background: var(--card-background-color, transparent);
    }
    .conn-search:focus {
        outline: none;
        border-color: var(--primary-color);
    }
    .conn-select {
        flex: 0 1 110px;
        min-width: 0;
        border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
        border-radius: 8px;
        padding: 6px 6px;
        font-size: 12px;
        font-family: inherit;
        color: var(--primary-text-color);
        background: var(--card-background-color, transparent);
    }
    .conn-reset {
        border: none;
        border-radius: 8px;
        padding: 6px 10px;
        font-size: 12px;
        font-family: inherit;
        cursor: pointer;
        color: var(--primary-color);
        background: var(--secondary-background-color, rgba(0, 0, 0, 0.05));
    }
    .conn-list {
        display: flex;
        flex-direction: column;
        gap: 2px;
        max-height: 260px;
        overflow-y: auto;
    }
    .conn-row {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 5px 2px;
        border-bottom: 1px solid var(--divider-color, rgba(0, 0, 0, 0.06));
    }
    .conn-row:last-child { border-bottom: none; }
    .conn-main {
        display: flex;
        flex-direction: column;
        min-width: 0;
        flex: 1 1 auto;
    }
    .conn-host {
        font-size: 12px;
        color: var(--primary-text-color);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .conn-sub {
        font-size: 11px;
        color: var(--secondary-text-color);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .conn-stats {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        flex: none;
        font-size: 11px;
        font-variant-numeric: tabular-nums;
        color: var(--secondary-text-color);
    }
    .conn-stat {
        display: inline-flex;
        align-items: center;
        gap: 2px;
    }
    .conn-stat.up ha-icon { color: #ff7043; --mdc-icon-size: 12px; }
    .conn-stat.down ha-icon { color: var(--success-color, #2e7d32); --mdc-icon-size: 12px; }
    .conn-age {
        color: var(--disabled-text-color);
        min-width: 34px;
        text-align: right;
    }
    .conn-close {
        flex: none;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border: none;
        border-radius: 6px;
        padding: 3px;
        cursor: pointer;
        color: var(--secondary-text-color);
        background: transparent;
        transition: background 0.15s ease, color 0.15s ease;
    }
    .conn-close:hover {
        color: var(--error-color, #c62828);
        background: color-mix(in srgb, var(--error-color, #c62828) 12%, transparent);
    }
    .conn-close ha-icon { --mdc-icon-size: 14px; }
    .conn-empty {
        padding: 14px 8px;
        text-align: center;
        font-size: 12px;
        color: var(--secondary-text-color);
    }
`;var Zt={loading:{ru:"\u0417\u0430\u0433\u0440\u0443\u0437\u043A\u0430 \u0434\u0430\u043D\u043D\u044B\u0445 sing-box\u2026",en:"Loading sing-box data\u2026"},testAll:{ru:"\u041F\u0440\u043E\u0432\u0435\u0440\u0438\u0442\u044C \u0432\u0441\u0435",en:"Test all"},testing:{ru:"\u0422\u0435\u0441\u0442\u2026",en:"Testing\u2026"},test:{ru:"\u0422\u0435\u0441\u0442",en:"Test"},speedUp:{ru:"\u0417\u0430\u0433\u0440\u0443\u0437\u043A\u0430",en:"Upload"},speedDown:{ru:"\u0421\u043A\u0430\u0447\u0438\u0432\u0430\u043D\u0438\u0435",en:"Download"},selectTitle:{ru:"\u0412\u044B\u0431\u0440\u0430\u0442\u044C {tag}",en:"Select {tag}"},pingTitle:{ru:"\u041F\u0440\u043E\u0432\u0435\u0440\u0438\u0442\u044C \u043F\u0438\u043D\u0433 {tag}",en:"Check ping of {tag}"},errors:{loadFailed:{ru:"\u041D\u0435 \u0443\u0434\u0430\u043B\u043E\u0441\u044C \u0437\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044C \u0434\u0430\u043D\u043D\u044B\u0435: {msg}",en:"Failed to load data: {msg}"},groupsDevice:{ru:"\u0413\u0440\u0443\u043F\u043F\u044B \u043F\u0440\u043E\u043A\u0441\u0438 \u043D\u0435 \u043D\u0430\u0439\u0434\u0435\u043D\u044B: \u043F\u043E device_id \u043D\u0430\u0439\u0434\u0435\u043D\u043E \u0437\u0430\u043F\u0438\u0441\u0435\u0439 \u0440\u0435\u0435\u0441\u0442\u0440\u0430: {count}, \u043D\u043E \u0441\u0443\u0449\u043D\u043E\u0441\u0442\u0435\u0439 ha-singbox \u0441\u0440\u0435\u0434\u0438 \u043D\u0438\u0445 \u043D\u0435\u0442 (select \u0432\u043E \u0432\u0441\u0451\u043C \u0440\u0435\u0435\u0441\u0442\u0440\u0435: {selects}, ping-\u0441\u0435\u043D\u0441\u043E\u0440\u043E\u0432: {pings}). \u041F\u0440\u0438\u043C\u0435\u0440 \u0437\u0430\u043F\u0438\u0441\u0435\u0439 \u043F\u043E device_id: {sample}. \u0423\u0431\u0435\u0434\u0438\u0442\u0435\u0441\u044C, \u0447\u0442\u043E \u0443\u0441\u0442\u0430\u043D\u043E\u0432\u043B\u0435\u043D\u0430 \u0438\u043D\u0442\u0435\u0433\u0440\u0430\u0446\u0438\u044F ha-singbox (Ghost-in-the-dark/ha-singbox) \u0438 \u043E\u043D\u0430 \u0441\u043E\u0437\u0434\u0430\u043B\u0430 \u0441\u0443\u0449\u043D\u043E\u0441\u0442\u0438, \u0437\u0430\u0442\u0435\u043C \u043F\u0435\u0440\u0435\u0437\u0430\u043F\u0443\u0441\u0442\u0438\u0442\u0435 HA.",en:"Proxy groups not found: device_id matched {count} registry records, but none of them are ha-singbox entities (selects across the registry: {selects}, ping sensors: {pings}). Sample records on the device: {sample}. Make sure the ha-singbox integration (Ghost-in-the-dark/ha-singbox) is installed and created entities, then restart HA."},groupsNone:{ru:"\u0413\u0440\u0443\u043F\u043F\u044B \u043F\u0440\u043E\u043A\u0441\u0438 \u043D\u0435 \u043D\u0430\u0439\u0434\u0435\u043D\u044B: \u0432 \u0440\u0435\u0435\u0441\u0442\u0440\u0435 \u043D\u0435\u0442 \u0441\u0443\u0449\u043D\u043E\u0441\u0442\u0435\u0439 sing-box (\u0432\u0441\u0435\u0433\u043E select: {selects}, ping-\u0441\u0435\u043D\u0441\u043E\u0440\u043E\u0432: {pings}). \u041F\u0440\u043E\u0432\u0435\u0440\u044C\u0442\u0435, \u0447\u0442\u043E ha-singbox \u0443\u0441\u0442\u0430\u043D\u043E\u0432\u043B\u0435\u043D\u0430 \u0438 \u043D\u0430\u0441\u0442\u0440\u043E\u0435\u043D\u0430, \u0437\u0430\u0442\u0435\u043C \u043F\u0435\u0440\u0435\u0437\u0430\u043F\u0443\u0441\u0442\u0438\u0442\u0435 HA.",en:"Proxy groups not found: the registry has no sing-box entities (selects in total: {selects}, ping sensors: {pings}). Check that ha-singbox is installed and configured, then restart HA."},groupsBadUid:{ru:"\u0413\u0440\u0443\u043F\u043F\u044B \u043F\u0440\u043E\u043A\u0441\u0438 \u043D\u0435 \u043D\u0430\u0439\u0434\u0435\u043D\u044B: select-\u0441\u0443\u0449\u043D\u043E\u0441\u0442\u0438 \u0435\u0441\u0442\u044C, \u043D\u043E \u0441 \u043D\u0435\u043E\u0436\u0438\u0434\u0430\u043D\u043D\u044B\u043C \u0444\u043E\u0440\u043C\u0430\u0442\u043E\u043C unique_id ({sample}). \u041E\u0431\u043D\u043E\u0432\u0438\u0442\u0435 ha-singbox \u0438 \u043F\u0435\u0440\u0435\u0437\u0430\u043F\u0443\u0441\u0442\u0438\u0442\u0435 HA.",en:"Proxy groups not found: select entities exist but with an unexpected unique_id format ({sample}). Update ha-singbox and restart HA."}},fallback:{device:{ru:"device_id \xAB{device}\xBB \u043D\u0435 \u0434\u0430\u043B \u0433\u0440\u0443\u043F\u043F (\u0437\u0430\u043F\u0438\u0441\u0435\u0439 \u0440\u0435\u0435\u0441\u0442\u0440\u0430: {count}) \u2014 \u043F\u043E\u043A\u0430\u0437\u0430\u043D\u044B \u0432\u0441\u0435 \u044D\u043A\u0437\u0435\u043C\u043F\u043B\u044F\u0440\u044B sing-box.",en:"device_id \u201C{device}\u201D produced no groups ({count} registry records) \u2014 showing all sing-box instances."},entityNotFound:{ru:"entity \xAB{entity}\xBB \u043D\u0435 \u043D\u0430\u0439\u0434\u0435\u043D\u0430 \u0432 \u0440\u0435\u0435\u0441\u0442\u0440\u0435 \u2014 \u043F\u043E\u043A\u0430\u0437\u0430\u043D\u044B \u0432\u0441\u0435 \u044D\u043A\u0437\u0435\u043C\u043F\u043B\u044F\u0440\u044B sing-box.",en:"entity \u201C{entity}\u201D was not found in the registry \u2014 showing all sing-box instances."},entityNoGroups:{ru:"entity \xAB{entity}\xBB \u043D\u0435 \u0434\u0430\u043B\u0430 \u0433\u0440\u0443\u043F\u043F \u2014 \u043F\u043E\u043A\u0430\u0437\u0430\u043D\u044B \u0432\u0441\u0435 \u044D\u043A\u0437\u0435\u043C\u043F\u043B\u044F\u0440\u044B sing-box.",en:"entity \u201C{entity}\u201D produced no groups \u2014 showing all sing-box instances."}},chart:{down:{ru:"\u0421\u043A\u0430\u0447\u0438\u0432\u0430\u043D\u0438\u0435",en:"Download"},up:{ru:"\u0417\u0430\u0433\u0440\u0443\u0437\u043A\u0430",en:"Upload"},peak:{ru:"\u041F\u0438\u043A: {value}",en:"Peak: {value}"},now:{ru:"\u0421\u0435\u0439\u0447\u0430\u0441: \u2193 {down} \xB7 \u2191 {up}",en:"Now: \u2193 {down} \xB7 \u2191 {up}"},empty:{ru:"\u0421\u043E\u0431\u0438\u0440\u0430\u0435\u043C \u0434\u0430\u043D\u043D\u044B\u0435 \u0434\u043B\u044F \u0433\u0440\u0430\u0444\u0438\u043A\u0430\u2026",en:"Collecting chart data\u2026"}},connections:{title:{ru:"\u041F\u043E\u0434\u043A\u043B\u044E\u0447\u0435\u043D\u0438\u044F",en:"Connections"},count:{ru:"\u0432\u0441\u0435\u0433\u043E: {total}",en:"total: {total}"},countFiltered:{ru:"{shown} \u0438\u0437 {total}",en:"{shown} of {total}"},search:{ru:"\u041F\u043E\u0438\u0441\u043A: \u0445\u043E\u0441\u0442, \u043F\u0440\u043E\u0446\u0435\u0441\u0441, \u043F\u0440\u0430\u0432\u0438\u043B\u043E\u2026",en:"Search: host, process, rule\u2026"},network:{ru:"\u0421\u0435\u0442\u044C",en:"Network"},protocol:{ru:"\u041F\u0440\u043E\u0442\u043E\u043A\u043E\u043B",en:"Protocol"},outbound:{ru:"Outbound",en:"Outbound"},allNetworks:{ru:"\u0412\u0441\u0435 \u0441\u0435\u0442\u0438",en:"All networks"},allProtocols:{ru:"\u0412\u0441\u0435 \u043F\u0440\u043E\u0442\u043E\u043A\u043E\u043B\u044B",en:"All protocols"},allOutbounds:{ru:"\u0412\u0441\u0435 outbound",en:"All outbounds"},reset:{ru:"\u0421\u0431\u0440\u043E\u0441\u0438\u0442\u044C",en:"Reset"},close:{ru:"\u0417\u0430\u043A\u0440\u044B\u0442\u044C \u043F\u043E\u0434\u043A\u043B\u044E\u0447\u0435\u043D\u0438\u0435",en:"Close connection"},closeAll:{ru:"\u0417\u0430\u043A\u0440\u044B\u0442\u044C \u0432\u0441\u0435",en:"Close all"},empty:{ru:"\u0410\u043A\u0442\u0438\u0432\u043D\u044B\u0445 \u043F\u043E\u0434\u043A\u043B\u044E\u0447\u0435\u043D\u0438\u0439 \u043D\u0435\u0442",en:"No active connections"},noMatch:{ru:"\u041D\u0438\u0447\u0435\u0433\u043E \u043D\u0435 \u043D\u0430\u0439\u0434\u0435\u043D\u043E \u043F\u043E \u0444\u0438\u043B\u044C\u0442\u0440\u0443",en:"Nothing matches the filter"},unsupported:{ru:"\u042D\u0442\u043E\u0442 \u0431\u044D\u043A\u0435\u043D\u0434 sing-box \u043D\u0435 \u043E\u0442\u0434\u0430\u0451\u0442 \u0441\u043F\u0438\u0441\u043E\u043A \u043F\u043E\u0434\u043A\u043B\u044E\u0447\u0435\u043D\u0438\u0439.",en:"This sing-box backend does not expose the connection list."},unavailable:{ru:"\u0421\u043F\u0438\u0441\u043E\u043A \u043F\u043E\u0434\u043A\u043B\u044E\u0447\u0435\u043D\u0438\u0439 \u043D\u0435\u0434\u043E\u0441\u0442\u0443\u043F\u0435\u043D: {msg}",en:"Connection list unavailable: {msg}"}},editor:{sections:{ru:"\u0427\u0442\u043E \u043F\u043E\u043A\u0430\u0437\u044B\u0432\u0430\u0442\u044C \u043D\u0430 \u043A\u0430\u0440\u0442\u043E\u0447\u043A\u0435",en:"Sections shown on the card"},sectionsHint:{ru:"\u041E\u0442\u043A\u043B\u044E\u0447\u0438\u0442\u0435 \u0431\u043B\u043E\u043A\u0438, \u043A\u043E\u0442\u043E\u0440\u044B\u0435 \u043D\u0435 \u043D\u0443\u0436\u043D\u044B. \u041D\u0430\u0441\u0442\u0440\u043E\u0439\u043A\u0438 \u043E\u0441\u0442\u0430\u044E\u0442\u0441\u044F \u0432 \u043A\u043E\u043D\u0444\u0438\u0433\u0435 \u0438 \u0432\u043A\u043B\u044E\u0447\u0430\u044E\u0442\u0441\u044F \u043E\u0431\u0440\u0430\u0442\u043D\u043E \u043E\u0434\u043D\u0438\u043C \u043F\u0435\u0440\u0435\u043A\u043B\u044E\u0447\u0430\u0442\u0435\u043B\u0435\u043C.",en:"Turn off the blocks you do not need. The settings stay in the config and come back with one switch."},show_test_all:{ru:"\u041A\u043D\u043E\u043F\u043A\u0430 \xAB\u041F\u0440\u043E\u0432\u0435\u0440\u0438\u0442\u044C \u0432\u0441\u0435\xBB",en:"\u201CTest all\u201D button"},show_speeds:{ru:"\u0422\u0435\u043A\u0443\u0449\u0430\u044F \u0441\u043A\u043E\u0440\u043E\u0441\u0442\u044C (\u043F\u043B\u0438\u0442\u043A\u0438)",en:"Current speed (tiles)"},show_chart:{ru:"\u0413\u0440\u0430\u0444\u0438\u043A \u0442\u0440\u0430\u0444\u0438\u043A\u0430",en:"Traffic chart"},show_totals:{ru:"\u0421\u0432\u043E\u0434\u043A\u0430: \u0432\u0441\u0435\u0433\u043E, \u043F\u0430\u043C\u044F\u0442\u044C, \u0441\u043E\u0435\u0434\u0438\u043D\u0435\u043D\u0438\u044F",en:"Totals: traffic, memory, connections"},show_groups:{ru:"\u0413\u0440\u0443\u043F\u043F\u044B \u0438 outbound",en:"Groups and outbounds"},show_connections:{ru:"\u0421\u043F\u0438\u0441\u043E\u043A \u043F\u043E\u0434\u043A\u043B\u044E\u0447\u0435\u043D\u0438\u0439",en:"Connections list"},title:{ru:"\u0417\u0430\u0433\u043E\u043B\u043E\u0432\u043E\u043A",en:"Title"},language:{ru:"\u042F\u0437\u044B\u043A \u0438\u043D\u0442\u0435\u0440\u0444\u0435\u0439\u0441\u0430",en:"Interface language"},languageAuto:{ru:"\u0410\u0432\u0442\u043E (\u043A\u0430\u043A \u0432 Home Assistant)",en:"Auto (follow Home Assistant)"},interval:{ru:"\u0421\u043A\u043E\u0440\u043E\u0441\u0442\u044C \u043E\u0431\u043D\u043E\u0432\u043B\u0435\u043D\u0438\u044F",en:"Update interval"},intervalLive:{ru:"\u0412 \u0440\u0435\u0430\u043B\u044C\u043D\u043E\u043C \u0432\u0440\u0435\u043C\u0435\u043D\u0438",en:"Real time (default)"},intervalSec:{ru:"{n} \u0441\u0435\u043A",en:"{n} s"},intervalHint:{ru:"\u041A\u0430\u043A \u0447\u0430\u0441\u0442\u043E \u043E\u0431\u043D\u043E\u0432\u043B\u044F\u0442\u044C \u043F\u043E\u043A\u0430\u0437\u0430\u043D\u0438\u044F \u043D\u0430 \u043A\u0430\u0440\u0442\u043E\u0447\u043A\u0435. 0 \u2014 \u043F\u0440\u0438 \u043A\u0430\u0436\u0434\u043E\u043C \u0438\u0437\u043C\u0435\u043D\u0435\u043D\u0438\u0438 \u0441\u043E\u0441\u0442\u043E\u044F\u043D\u0438\u044F \u0432 HA (\u043F\u043E \u0443\u043C\u043E\u043B\u0447\u0430\u043D\u0438\u044E). \u0412\u044B\u0431\u043E\u0440 outbound \u0438 \u043A\u043D\u043E\u043F\u043A\u0438 \u0442\u0435\u0441\u0442\u0430 \u0432\u0441\u0435\u0433\u0434\u0430 \u043F\u0440\u0438\u043C\u0435\u043D\u044F\u044E\u0442\u0441\u044F \u0441\u0440\u0430\u0437\u0443.",en:"How often the card refreshes its values. 0 \u2014 on every HA state change (default). Outbound selection and the test buttons always apply instantly."},showTestAll:{ru:"\u041A\u043D\u043E\u043F\u043A\u0430 \xAB\u041F\u0440\u043E\u0432\u0435\u0440\u0438\u0442\u044C \u0432\u0441\u0435\xBB",en:"\u201CTest all\u201D button"},showTestAllHint:{ru:"\u041C\u0430\u0441\u0441\u043E\u0432\u044B\u0439 url-test \u043F\u043E \u0432\u0441\u0435\u043C \u0433\u0440\u0443\u043F\u043F\u0430\u043C \u0438 outbound \u0432 \u043E\u0434\u0438\u043D \u043A\u043B\u0438\u043A.",en:"Batch url-test of every group and outbound in one tap."},exclude:{ru:"\u0421\u043A\u0440\u044B\u0442\u044C outbound \u0438\u0437 \u043A\u0430\u0440\u0442\u043E\u0447\u043A\u0438",en:"Hide outbounds from the card"},excludeHint:{ru:"\u041E\u0442\u043C\u0435\u0447\u0435\u043D\u043D\u044B\u0435 \u0442\u0435\u0433\u0438 \u043D\u0435 \u043F\u043E\u043A\u0430\u0437\u044B\u0432\u0430\u044E\u0442\u0441\u044F \u0432 \u0433\u0440\u0443\u043F\u043F\u0430\u0445 \u0438 \u0431\u043B\u043E\u043A\u0435 Outbound.",en:"Checked tags are hidden from the groups and the Outbound block."},device:{ru:"device_id (\u043D\u0435\u043E\u0431\u044F\u0437\u0430\u0442\u0435\u043B\u044C\u043D\u043E)",en:"device_id (optional)"},deviceHint:{ru:"\u041F\u0440\u0438\u0432\u044F\u0437\u043A\u0430 \u043A \u043A\u043E\u043D\u043A\u0440\u0435\u0442\u043D\u043E\u043C\u0443 \u0443\u0441\u0442\u0440\u043E\u0439\u0441\u0442\u0432\u0443 sing-box, \u0435\u0441\u043B\u0438 \u0438\u0445 \u043D\u0435\u0441\u043A\u043E\u043B\u044C\u043A\u043E.",en:"Pin to a specific sing-box device when several are configured."},entity:{ru:"entity (\u043D\u0435\u043E\u0431\u044F\u0437\u0430\u0442\u0435\u043B\u044C\u043D\u043E)",en:"entity (optional)"},entityHint:{ru:"\u0410\u043B\u044C\u0442\u0435\u0440\u043D\u0430\u0442\u0438\u0432\u043D\u0430\u044F \u043F\u0440\u0438\u0432\u044F\u0437\u043A\u0430 \u0447\u0435\u0440\u0435\u0437 \u043B\u044E\u0431\u0443\u044E \u0441\u0443\u0449\u043D\u043E\u0441\u0442\u044C ha-singbox.",en:"Alternative pin via any ha-singbox entity."}}};function D(o,t){let e=o&&o.language||"auto";if(e==="ru"||e==="en")return e;let n=t&&(t.language||t.locale&&t.locale.language)||"";return String(n).toLowerCase().startsWith("ru")?"ru":"en"}function Qt(o){return o.split(".").reduce((t,e)=>t&&t[e],Zt)}function F(o,t,e={}){let n=Qt(t),i=n&&(n[o]||n.en)||t;return Object.entries(e).reduce((s,[r,a])=>s.split(`{${r}}`).join(String(a)),i)}var te=[0,1,2,3,5,10,30,60],ee="_group_",rt="_ping_",ne="_clash_mode",ie="GLOBAL",se=["show_test_all","show_speeds","show_chart","show_totals","show_groups","show_connections"],at=class extends m{static properties={hass:{},_config:{state:!0},_candidates:{state:!0}};static styles=E`
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
    `;setConfig(t){this._config={...t},this._loadCandidates()}firstUpdated(){this._loadCandidates()}updated(t){t.has("hass")&&this._loadCandidates()}_lang(){return D(this._config,this.hass)}_t(t,e={}){return F(this._lang(),t,e)}_update(t,e){this._config={...this._config,[t]:e},this.dispatchEvent(new CustomEvent("config-changed",{detail:{config:this._config},bubbles:!0,composed:!0}))}_onText(t,e){this._update(e,t.target.value)}_onSwitch(t,e){this._update(e,t.target.checked)}_onSelectChange(t,e){t.detail&&"value"in t.detail||this._applySelect(e,t.target&&t.target.value)}_onSelectSelected(t,e){!t.detail||!("value"in t.detail)||this._applySelect(e,t.detail.value)}_applySelect(t,e){e==null||e===""||(t==="update_interval"&&(e=Number(e)),this._update(t,e))}_toggleExclude(t,e){let n=new Set(this._config.exclude_outbounds||[]);e?n.add(t):n.delete(t),this._update("exclude_outbounds",[...n].sort())}async _loadCandidates(){if(!(this._candidates!==void 0||this._loading)&&!(!this.hass||typeof this.hass.callWS!="function")){this._loading=!0;try{let t=await this.hass.callWS({type:"config/entity_registry/list"});this._candidates=this._candidateTags(t||[])}catch{this._candidates=[]}finally{this._loading=!1}}}_candidateTags(t){let e=this._config&&this._config.device_id,n=new Set;for(let i of t){if(i.platform!=="singbox"||e&&i.device_id!==e)continue;let s=i.unique_id||"",r=(i.entity_id||"").split(".")[0];if(r==="sensor"&&s.includes(rt)){let a=s.slice(s.lastIndexOf(rt)+rt.length);a!==ie&&n.add(a)}else if(r==="select"&&s.includes(ee)&&!s.endsWith(ne)){let a=this.hass.states&&this.hass.states[i.entity_id];(a&&a.attributes&&Array.isArray(a.attributes.options)?a.attributes.options:[]).forEach(l=>n.add(l))}}return[...n].sort((i,s)=>i.localeCompare(s))}_languageOptions(){return[{value:"auto",label:this._t("editor.languageAuto")},{value:"ru",label:"\u0420\u0443\u0441\u0441\u043A\u0438\u0439"},{value:"en",label:"English"}]}_intervalOptions(){return te.map(t=>({value:String(t),label:this._intervalLabel(t)}))}_intervalLabel(t){return t===0?this._t("editor.intervalLive"):this._t("editor.intervalSec",{n:t})}render(){let t=this._config||{},e=Number(t.update_interval)||0,n=new Set(t.exclude_outbounds||[]),i=this._languageOptions(),s=this._intervalOptions(),r=(this._candidates||[]).length>0;return p`
            <ha-textfield
                label=${this._t("editor.title")}
                value=${t.title||"Sing-box"}
                @change=${a=>this._onText(a,"title")}
            ></ha-textfield>

            <div class="block">
                <ha-select
                    label=${this._t("editor.language")}
                    .value=${t.language||"auto"}
                    .options=${i}
                    @change=${a=>this._onSelectChange(a,"language")}
                    @selected=${a=>this._onSelectSelected(a,"language")}
                >
                    ${i.map(a=>p`
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
                    .options=${s}
                    @change=${a=>this._onSelectChange(a,"update_interval")}
                    @selected=${a=>this._onSelectSelected(a,"update_interval")}
                >
                    ${s.map(a=>p`
                            <mwc-list-item value=${a.value}>
                                ${a.label}
                            </mwc-list-item>
                        `)}
                </ha-select>
                <div class="hint">${this._t("editor.intervalHint")}</div>
            </div>

            <div class="block">
                <div class="block-title">${this._t("editor.sections")}</div>
                <div class="hint">${this._t("editor.sectionsHint")}</div>
                ${se.map(a=>p`
                        <div class="row">
                            <span class="label"
                                >${this._t(`editor.${a}`)}</span
                            >
                            <ha-switch
                                .checked=${t[a]!==!1}
                                @change=${c=>this._onSwitch(c,a)}
                            ></ha-switch>
                        </div>
                    `)}
            </div>

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
                                          .checked=${n.has(a)}
                                          @change=${c=>this._toggleExclude(a,c.target.checked)}
                                      ></ha-switch>
                                  </div>
                              `)}
                      </div>
                  `:p`
                      <ha-textfield
                          label=${this._t("editor.exclude")}
                          value=${(t.exclude_outbounds||[]).join(", ")}
                          @change=${a=>this._update("exclude_outbounds",a.target.value.split(",").map(c=>c.trim()).filter(Boolean))}
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
        `}};customElements.get("singbox-panel-card-editor")||customElements.define("singbox-panel-card-editor",at);var oe=[0,25,50,75,100];function j(o,t,e){return Math.min(Math.max(Number(o)||0,t),e)}function ct(o){if(!(o>0))return 1;let t=10**Math.floor(Math.log10(o)),e=o/t;return(e<=1?1:e<=2?2:e<=2.5?2.5:e<=5?5:10)*t}function lt(o,t,e,n){let i=Math.max(e-t,1);return o.map(s=>{let r=j((s.t-t)/i*100,0,100),a=100-j(s.v,0,n)/n*100;return`${r.toFixed(2)},${a.toFixed(2)}`}).join(" ")}function Pt(o,t,e,n){if(o.length===0)return"";let i=Math.max(e-t,1),s=o[0],r=o[o.length-1],a=j((s.t-t)/i*100,0,100),c=j((r.t-t)/i*100,0,100),l=lt(o,t,e,n);return`${a.toFixed(2)},100 ${l} ${c.toFixed(2)},100`}function Mt({samples:o,startMs:t,endMs:e,emptyText:n,peakText:i,scaleText:s=""}){let r=o.length>1,a=o.reduce((h,_)=>Math.max(h,_.up||0,_.down||0),0),c=ct(a),l=o.map(h=>({t:h.t,v:h.up||0})),d=o.map(h=>({t:h.t,v:h.down||0}));return k`
        <div class="chart">
            <div class="chart-head">
                <span class="chart-peak">${i}</span>
                ${r&&s?k`<span class="chart-scale">${s}</span>`:""}
            </div>
            <svg
                class="chart-svg"
                viewBox="0 0 100 100"
                preserveAspectRatio="none"
                role="img"
                aria-label=${i}
            >
                ${oe.map(h=>k`<line
                        class="chart-grid"
                        x1="0"
                        y1=${h}
                        x2="100"
                        y2=${h}
                        vector-effect="non-scaling-stroke"
                    ></line>`)}
                ${r?k`
                          <polygon
                              class="chart-fill down"
                              points=${Pt(d,t,e,c)}
                          ></polygon>
                          <polyline
                              class="chart-line down"
                              points=${lt(d,t,e,c)}
                              vector-effect="non-scaling-stroke"
                          ></polyline>
                          <polygon
                              class="chart-fill up"
                              points=${Pt(l,t,e,c)}
                          ></polygon>
                          <polyline
                              class="chart-line up"
                              points=${lt(l,t,e,c)}
                              vector-effect="non-scaling-stroke"
                          ></polyline>
                      `:""}
            </svg>
            ${r?"":k`<div class="chart-empty">${n}</div>`}
        </div>
    `}function Ot(o){if(!o||typeof o!="object")return null;let t=String(o.id??"");return t?{id:t,network:String(o.network??""),protocol:String(o.protocol??""),source:String(o.source??""),destination:String(o.destination??""),host:String(o.host??o.domain??""),rule:String(o.rule??""),outbound:String(o.outbound??""),chain:Array.isArray(o.chain)?o.chain.map(String):[],process:String(o.process??""),upload:H(o.upload),download:H(o.download),uploadTotal:H(o.upload_total??o.uploadTotal),downloadTotal:H(o.download_total??o.downloadTotal),startedAt:H(o.created_at??o.createdAt)}:null}function H(o){let t=Number(o);return Number.isFinite(t)?t:0}function Rt(o,t={}){let e=String(t.query??"").trim().toLowerCase(),n=String(t.network??""),i=String(t.protocol??""),s=String(t.outbound??"");return o.filter(r=>n&&r.network!==n||i&&r.protocol!==i||s&&r.outbound!==s?!1:e?[r.host,r.process,r.outbound,r.rule,r.destination,r.source,r.protocol,r.network].join(" ").toLowerCase().includes(e):!0)}function G(o,t){let e=new Set;for(let n of o){let i=n[t];i&&e.add(i)}return[...e].sort((n,i)=>n.localeCompare(i))}function Ht(o){return[...o].sort((t,e)=>e.startedAt!==t.startedAt?e.startedAt-t.startedAt:e.downloadTotal+e.uploadTotal-(t.downloadTotal+t.uploadTotal))}function Ut({connections:o,total:t,filter:e,networks:n,protocols:i,outbounds:s,onFilter:r,onClose:a,onCloseAll:c,closingAll:l,t:d,formatBytes:h,formatAge:_}){let f=!!(e.query||e.network||e.protocol||e.outbound);return p`
        <div class="connections">
            <div class="conn-head">
                <span class="conn-title">${d("connections.title")}</span>
                <span class="conn-count">
                    ${f?d("connections.countFiltered",{shown:o.length,total:t}):d("connections.count",{total:t})}
                </span>
                ${t>0?p`<button
                          class="conn-close-all"
                          ?disabled=${l}
                          title=${d("connections.closeAll")}
                          @click=${()=>c()}
                      >
                          <ha-icon icon="mdi:close-circle-multiple-outline"></ha-icon>
                      </button>`:""}
            </div>

            ${t>0?p`
                      <div class="conn-filters">
                          <input
                              class="conn-search"
                              type="search"
                              .value=${e.query||""}
                              placeholder=${d("connections.search")}
                              aria-label=${d("connections.search")}
                              @input=${u=>r({query:u.target.value})}
                          />
                          <select
                              class="conn-select"
                              aria-label=${d("connections.network")}
                              .value=${e.network||""}
                              @change=${u=>r({network:u.target.value})}
                          >
                              <option value="">${d("connections.allNetworks")}</option>
                              ${n.map(u=>p`<option
                                      value=${u}
                                      ?selected=${e.network===u}
                                  >
                                      ${u}
                                  </option>`)}
                          </select>
                          <select
                              class="conn-select"
                              aria-label=${d("connections.protocol")}
                              .value=${e.protocol||""}
                              @change=${u=>r({protocol:u.target.value})}
                          >
                              <option value="">${d("connections.allProtocols")}</option>
                              ${i.map(u=>p`<option
                                      value=${u}
                                      ?selected=${e.protocol===u}
                                  >
                                      ${u}
                                  </option>`)}
                          </select>
                          <select
                              class="conn-select"
                              aria-label=${d("connections.outbound")}
                              .value=${e.outbound||""}
                              @change=${u=>r({outbound:u.target.value})}
                          >
                              <option value="">${d("connections.allOutbounds")}</option>
                              ${s.map(u=>p`<option
                                      value=${u}
                                      ?selected=${e.outbound===u}
                                  >
                                      ${u}
                                  </option>`)}
                          </select>
                          ${f?p`<button
                                    class="conn-reset"
                                    @click=${()=>r({query:"",network:"",protocol:"",outbound:""})}
                                >
                                    ${d("connections.reset")}
                                </button>`:""}
                      </div>
                  `:""}

            ${o.length===0?p`<div class="conn-empty">
                      ${d(t===0?"connections.empty":"connections.noMatch")}
                  </div>`:p`<div class="conn-list">
                      ${o.map(u=>p`
                              <div class="conn-row">
                                  <div class="conn-main">
                                      <span class="conn-host">
                                          ${u.host||u.destination||u.source}
                                      </span>
                                      <span class="conn-sub">
                                          ${[u.protocol,u.network,u.outbound].filter(Boolean).join(" \xB7 ")}
                                      </span>
                                  </div>
                                  <div class="conn-stats">
                                      <span class="conn-stat up">
                                          <ha-icon icon="mdi:arrow-up"></ha-icon>
                                          ${h(u.uploadTotal)}
                                      </span>
                                      <span class="conn-stat down">
                                          <ha-icon icon="mdi:arrow-down"></ha-icon>
                                          ${h(u.downloadTotal)}
                                      </span>
                                      <span class="conn-age">
                                          ${_(u.startedAt)}
                                      </span>
                                  </div>
                                  <button
                                      class="conn-close"
                                      title=${d("connections.close")}
                                      @click=${()=>a(u.id)}
                                  >
                                      <ha-icon icon="mdi:close"></ha-icon>
                                  </button>
                              </div>
                          `)}
                  </div>`}
        </div>
    `}var re="0.1.17",U="_group_",L="_ping_",W="_clash_mode",ae="GLOBAL",le=1e4,Lt="Sing-box",zt=300,dt=5*60*1e3,ce=900,ht=class extends m{static properties={_state:{state:!0},_model:{state:!0},_testing:{state:!0},_testingAll:{state:!0}};static styles=Nt;constructor(){super(),this._hass=null,this._config={},this._discovered=!1,this._state="loading",this._model=null,this._testing={},this._testingAll=!1,this._fallbackNote=null,this._error=null,this._lastRenderAt=0,this._renderTimer=null,this._pendingSelections={},this._chartSamples=[],this._connections=[],this._connectionsSupported=!0,this._connectionsError=null,this._connFilter={query:"",network:"",protocol:"",outbound:""},this._closingAll=!1,this._connPollTimer=null,this._connFetchInFlight=!1,this._chartTimer=null}static getStubConfig(){return{title:Lt,show_test_all:!0,show_speeds:!0,show_totals:!0,show_chart:!0,show_groups:!0,show_connections:!0,exclude_outbounds:[],update_interval:0,language:"auto"}}static getConfigElement(){return document.createElement("singbox-panel-card-editor")}setConfig(t){if(!t||typeof t!="object")throw new Error("Invalid configuration");let e=this._config||{},n={title:Lt,show_test_all:!0,show_speeds:!0,show_totals:!0,show_chart:!0,show_groups:!0,show_connections:!0,exclude_outbounds:[],update_interval:0,language:"auto",...t};for(let s of["show_test_all","show_speeds","show_totals","show_chart","show_groups","show_connections"])n[s]=n[s]!==!1;n.exclude_outbounds=(Array.isArray(n.exclude_outbounds)?n.exclude_outbounds:String(n.exclude_outbounds??"").split(",")).map(s=>String(s).trim()).filter(Boolean);let i=Number(n.update_interval);n.update_interval=Number.isFinite(i)&&i>0?Math.min(i,3600):0,this._config=n,this._discovered&&this._needsRediscovery(e,n)&&(this._discovered=!1,this._hass&&this._discover()),this.requestUpdate()}_needsRediscovery(t,e){if(t.device_id!==e.device_id||t.entity!==e.entity)return!0;let n=t.exclude_outbounds||[],i=e.exclude_outbounds||[];return n.length!==i.length||i.some(s=>!n.includes(s))}getCardSize(){return 4}get hass(){return this._hass}set hass(t){this._hass=t,t&&!this._discovered&&(this._discovered=!0,this._discover()),t&&this._recordChartSample(),t&&this._scheduleRender()}connectedCallback(){super.connectedCallback(),this._discovered&&this._startConnectionPolling()}disconnectedCallback(){super.disconnectedCallback(),this._stopConnectionPolling()}_lang(){return D(this._config,this._hass)}_t(t,e={}){return F(this._lang(),t,e)}async _discover(){this._state="loading",this._fallbackNote=null;try{let t=await this._hass.callWS({type:"config/entity_registry/list"});if(!Array.isArray(t))throw new Error("registry is unavailable");let e=s=>this._domain(s)==="select"&&s.unique_id&&s.unique_id.includes(U)&&!s.unique_id.endsWith(W),n=s=>s.filter(e),i=t;if(this._config.device_id){let s=t.filter(r=>r.device_id===this._config.device_id);n(s).length>0?i=s:this._fallbackNote={key:"fallback.device",params:{device:this._config.device_id,count:s.length}}}else if(this._config.entity){let s=t.find(r=>r.entity_id===this._config.entity);if(!s)this._fallbackNote={key:"fallback.entityNotFound",params:{entity:this._config.entity}};else{let r=t.filter(a=>s.config_entry_id&&a.config_entry_id===s.config_entry_id||s.device_id&&a.device_id===s.device_id);n(r).length>0?i=r:this._fallbackNote={key:"fallback.entityNoGroups",params:{entity:this._config.entity}}}}if(this._model=this._buildModel(i),this._model.groups.length===0){let s=t.filter(_=>this._domain(_)==="select"),r=n(t),a=t.filter(_=>this._domain(_)==="sensor"&&_.unique_id&&_.unique_id.includes(L)),c=this._config.device_id?t.filter(_=>_.device_id===this._config.device_id).length:null,l=this._config.device_id?t.filter(_=>_.device_id===this._config.device_id):[],d=l.slice(0,5).map(_=>{let f=_.unique_id?_.unique_id.slice(0,40):"\u2014";return`${_.entity_id} (${this._domain(_)}) [${f}]`}).join(", ");l.length&&console.warn("singbox-panel: records matched by pin:",l.map(_=>`${_.entity_id} ${this._domain(_)} ${_.unique_id??""}`).join(`
`));let h=r.slice(0,5).map(_=>`${_.entity_id} [${_.unique_id}]`).join(", ");this._state="error",r.length===0&&c!==null?this._error={key:"errors.groupsDevice",params:{count:c,selects:s.length,pings:a.length,sample:d}}:r.length===0?this._error={key:"errors.groupsNone",params:{selects:s.length,pings:a.length}}:this._error={key:"errors.groupsBadUid",params:{sample:h}};return}this._fallbackNote&&console.warn(`singbox-panel: ${this._t(this._fallbackNote.key,this._fallbackNote.params)}`),this._state="ready",this._startConnectionPolling(),this._fetchConnections()}catch(t){this._state="error",this._error={key:"errors.loadFailed",params:{msg:t&&t.message?t.message:String(t)}}}}_buildModel(t){let e=new Set(this._config.exclude_outbounds||[]);this._discoveredEntryId=null;for(let l of t){if(!l||!l.config_entry_id||!l.unique_id)continue;if(l.unique_id.includes(U)||l.unique_id.includes(L)||l.unique_id.endsWith(W)){this._discoveredEntryId=l.config_entry_id;break}}let n={};for(let l of t)if(this._domain(l)==="sensor"&&l.unique_id&&l.unique_id.includes(L)){let d=l.unique_id.slice(l.unique_id.lastIndexOf(L)+L.length);if(d===ae)continue;n[d]=l.entity_id}let i=[],s=new Set;for(let l of t){if(this._domain(l)!=="select"||!l.unique_id||!l.unique_id.includes(U)||l.unique_id.endsWith(W))continue;let d=l.unique_id.slice(l.unique_id.lastIndexOf(U)+U.length),h=this._hass.states[l.entity_id],_=h&&h.attributes&&Array.isArray(h.attributes.options)?h.attributes.options:[];_.forEach(u=>s.add(u));let f=_.filter(u=>!e.has(u)).map(u=>({tag:u,pingEntity:n[u]||null}));f.length!==0&&i.push({tag:d,entityId:l.entity_id,options:f})}let r=Object.keys(n).filter(l=>!s.has(l)&&!e.has(l)).sort().map(l=>({tag:l,pingEntity:n[l]})),a=l=>{let d=t.find(h=>this._domain(h)==="sensor"&&h.unique_id&&h.unique_id.endsWith(l));return d?d.entity_id:null},c=t.find(l=>this._domain(l)==="select"&&l.unique_id&&l.unique_id.endsWith(W));return{version:a("_version"),uplink:a("_uplink"),downlink:a("_downlink"),uplinkTotal:a("_uplink_total"),downlinkTotal:a("_downlink_total"),memory:a("_memory"),connectionsIn:a("_connections_in"),clashMode:c?c.entity_id:null,groups:i,standalone:r}}_entity(t){return t?this._hass.states[t]:void 0}_domain(t){return t.entity_id?t.entity_id.split(".")[0]:t.domain||""}_stateValue(t){let e=this._entity(t);return e?e.state==="unavailable"?null:e.state:null}_formatSpeed(t){let e=this._entity(t);if(!e||e.state==="unavailable"||e.state==="unknown")return{value:"\u2014",unit:""};let n=Number(e.state);return Number.isFinite(n)?{value:n.toLocaleString(void 0,{maximumFractionDigits:1}),unit:e.attributes&&e.attributes.unit_of_measurement?e.attributes.unit_of_measurement:""}:{value:"\u2014",unit:""}}_formatBytes(t){let e=this._entity(t);if(!e||e.state==="unavailable"||e.state==="unknown")return"\u2014";let n=Number(e.state);if(!Number.isFinite(n))return"\u2014";let i=e.attributes&&e.attributes.unit_of_measurement||"B",s={B:1,kB:1e3,MB:1e6,GB:1e9,TB:1e12,KiB:1024,MiB:1024**2,GiB:1024**3,TiB:1024**4},r=n*(s[i]||1),a=["B","KiB","MiB","GiB","TiB"],c=r,l=0;for(;c>=1024&&l<a.length-1;)c/=1024,l+=1;let d=l?1:0;return`${c.toLocaleString(void 0,{maximumFractionDigits:d})} ${a[l]}`}_ping(t){let e=this._entity(t.pingEntity);if(!e||e.state==="unavailable"||e.state==="unknown")return null;let n=Number(e.state);return Number.isFinite(n)?n:null}_pingClass(t){return t===null?"none":t<=100?"good":t<=300?"warn":"bad"}_pingText(t){return t===null?"\u2014":`${t} ms`}_recordChartSample(t=!1){if(!this._model)return;let e=this._speedValue(this._model.uplink),n=this._speedValue(this._model.downlink);if(e===null&&n===null)return;let i=Date.now(),s=this._chartSamples[this._chartSamples.length-1];if(!t&&s&&i-s.t<ce){s.up=e||0,s.down=n||0;return}this._chartSamples=[...this._chartSamples,{t:i,up:e||0,down:n||0}],this._pruneChartSamples(i)}_pruneChartSamples(t){let e=t-dt,n=this._chartSamples.filter(i=>i.t>=e);n.length>zt&&(n=n.slice(n.length-zt)),this._chartSamples=n}_speedValue(t){let e=this._entity(t);if(!e||e.state==="unavailable"||e.state==="unknown")return null;let n=Number(e.state);return Number.isFinite(n)?n:null}_chartCaption(){let t=this._model,e=this._chartSamples.reduce((s,r)=>Math.max(s,r.up||0,r.down||0),0),n=this._entity(t&&t.downlink)&&this._entity(t.downlink).attributes&&this._entity(t.downlink).attributes.unit_of_measurement||"",i=s=>s.toLocaleString(void 0,{maximumFractionDigits:1});return this._t("chart.peak",{value:`${i(e)} ${n}`.trim()})}_chartScaleText(){let t=ct(this._chartSamples.reduce((i,s)=>Math.max(i,s.up||0,s.down||0),0)),e=this._entity(this._model&&this._model.downlink)&&this._entity(this._model.downlink).attributes&&this._entity(this._model.downlink).attributes.unit_of_measurement||"";return`0 \u2013 ${(i=>i.toLocaleString(void 0,{maximumFractionDigits:1}))(t)} ${e}`.trim()}_renderChart(){let t=Date.now(),e=this._chartSamples[0],n=e?Math.max(e.t,t-dt):t-dt;return Mt({samples:this._chartSamples,startMs:n,endMs:t,emptyText:this._t("chart.empty"),peakText:this._chartSamples.length>1?this._chartCaption():"",scaleText:this._chartSamples.length>1?this._chartScaleText():""})}_startConnectionPolling(){if(this._connPollTimer)return;let t=this._refreshMs()>0?this._refreshMs():2e3,e=()=>{this._connPollTimer=setTimeout(()=>{this._fetchConnections(),e()},Math.max(t,1e3))};e(),this._startChartTimer()}_startChartTimer(){if(this._chartTimer)return;let t=()=>{this._chartTimer=setTimeout(()=>{this._recordChartSample(),this._scheduleRender(),t()},1e3)};t()}_stopChartTimer(){this._chartTimer&&(clearTimeout(this._chartTimer),this._chartTimer=null)}_stopConnectionPolling(){this._connPollTimer&&(clearTimeout(this._connPollTimer),this._connPollTimer=null),this._stopChartTimer()}async _fetchConnections(){if(!(!this._hass||this._connFetchInFlight)&&this._config.show_connections!==!1){this._connFetchInFlight=!0;try{let t={type:"singbox/connections"},e=this._entryId();e&&(t.entry_id=e);let n;try{n=await this._hass.callWS(t)}catch(a){if(!e)throw a;n=await this._hass.callWS({type:"singbox/connections"})}let i=n&&n.supported!==!1,s=Array.isArray(n&&n.connections)?n.connections.map(Ot).filter(Boolean):[],r=i!==this._connectionsSupported||i&&s.length!==this._connections.length;this._connectionsSupported=i,this._connections=i?Ht(s):[],this._connectionsError=null,r&&this._scheduleRender()}catch(t){let e=String(t&&t.message?t.message:t);/unknown command|not_found|not found/i.test(e)?(this._connectionsSupported=!1,this._connections=[],this._connectionsError=null):this._connectionsError={msg:e}}finally{this._connFetchInFlight=!1}}}_entryId(){return this._config.entry_id||this._discoveredEntryId||null}_setConnFilter(t){this._connFilter={...this._connFilter,...t},this._requestRender()}async _closeConnection(t){if(!(!this._hass||!t))try{await this._callService("singbox","close_connection",{connection_id:t}),this._connections=this._connections.filter(e=>e.id!==t),this._requestRender()}catch(e){console.error("singbox-panel: close_connection failed",e)}}async _closeAllConnections(){if(!(!this._hass||this._closingAll)){this._closingAll=!0;try{await this._callService("singbox","close_all_connections",{}),this._connections=[],this._requestRender()}catch(t){console.error("singbox-panel: close_all_connections failed",t)}finally{setTimeout(()=>{this._closingAll=!1},2e3)}}}_formatConnBytes(t){let e=["B","KiB","MiB","GiB","TiB"],n=Number(t)||0,i=0;for(;n>=1024&&i<e.length-1;)n/=1024,i+=1;let s=i?1:0;return`${n.toLocaleString(void 0,{maximumFractionDigits:s})} ${e[i]}`}_formatConnAge(t){if(!t)return"";let e=Math.max(0,Math.round((Date.now()-t)/1e3));if(e<60)return`${e}s`;let n=Math.floor(e/60);if(n<60)return`${n}m`;let i=Math.floor(n/60);return i<24?`${i}h`:`${Math.floor(i/24)}d`}_renderConnections(){if(this._config.show_connections===!1)return"";if(!this._connectionsSupported)return p`
                <div class="connections">
                    <div class="conn-head">
                        <span class="conn-title">${this._t("connections.title")}</span>
                    </div>
                    <div class="conn-empty">${this._t("connections.unsupported")}</div>
                </div>
            `;let t=this._connections;return Ut({connections:Rt(t,this._connFilter),total:t.length,filter:this._connFilter,networks:G(t,"network"),protocols:G(t,"protocol"),outbounds:G(t,"outbound"),onFilter:e=>this._setConnFilter(e),onClose:e=>this._closeConnection(e),onCloseAll:()=>this._closeAllConnections(),closingAll:this._closingAll,t:(e,n)=>this._t(e,n),formatBytes:e=>this._formatConnBytes(e),formatAge:e=>this._formatConnAge(e)})}_refreshMs(){let t=Number(this._config.update_interval)||0;return Math.min(Math.max(t,0),3600)*1e3}_scheduleRender(t=!1){if(!this._hass)return;let e=this._refreshMs();if(e<=0||t){this._requestRender();return}let n=Date.now(),i=this._lastRenderAt+e;if(n>=i){this._requestRender();return}this._renderTimer||(this._renderTimer=setTimeout(()=>{this._renderTimer=null,this._requestRender()},i-n))}_requestRender(){this._renderTimer&&(clearTimeout(this._renderTimer),this._renderTimer=null),this.requestUpdate()}_groupCurrent(t){let e=this._entity(t.entityId),n=e&&e.state!=="unavailable"?e.state:null,i=this._pendingSelections[t.entityId];return i?i.tag===n||Date.now()-i.ts>le?(delete this._pendingSelections[t.entityId],n):i.tag:n}async _callService(t,e,n,i){try{await this._hass.callService(t,e,i?{...n,entity_id:i}:n)}catch(s){let r=String(s&&s.message?s.message:s);if(i&&/extra keys not allowed/.test(r)){await this._hass.callService(t,e,n);return}throw s}}async _selectNode(t,e,n){if(!(!this._hass||!n)){this._pendingSelections[n]={tag:e,ts:Date.now()},this._scheduleRender(!0);try{await this._callService("singbox","select_outbound",{group_tag:t,outbound_tag:e},n)}catch(i){console.error("singbox-panel: select_outbound failed",i),delete this._pendingSelections[n]}this._scheduleRender(!0)}}async _testGroup(t){let e=t.options||[];if(!this._hass||this._testing[t.tag]||e.length===0)return;let n=Object.fromEntries(e.map(i=>[i.tag,!0]));this._testing={...this._testing,[t.tag]:!0,...n};try{await Promise.all(e.map(i=>this._callService("singbox","url_test",{outbound_tag:i.tag},i.pingEntity||t.entityId).catch(s=>{console.error(`singbox-panel: url_test failed for ${i.tag}`,s)})))}finally{setTimeout(()=>{let i={...this._testing};delete i[t.tag];for(let s of e)delete i[s.tag];this._testing=i},4e3)}}async _pingNode(t,e){if(!(!this._hass||this._testing[t])){this._testing={...this._testing,[t]:!0};try{await this._callService("singbox","url_test",{outbound_tag:t},e)}catch(n){console.error("singbox-panel: url_test failed",n)}finally{setTimeout(()=>{this._testing={...this._testing,[t]:!1}},4e3)}}}async _testAll(){if(!this._hass||!this._model||this._testingAll)return;this._testingAll=!0;let t=new Set,e=[];for(let n of this._model.groups)for(let i of n.options)t.has(i.tag)||(t.add(i.tag),e.push({tag:i.tag,target:i.pingEntity||n.entityId}));for(let n of this._model.standalone)t.has(n.tag)||(t.add(n.tag),e.push({tag:n.tag,target:n.pingEntity}));try{await Promise.all(e.map(n=>this._callService("singbox","url_test",{outbound_tag:n.tag},n.target).catch(i=>{console.error(`singbox-panel: url_test failed for ${n.tag}`,i)})))}finally{setTimeout(()=>{this._testingAll=!1},4e3)}}render(){if(this._lastRenderAt=Date.now(),this._state==="error"){let s=this._error||{key:"errors.loadFailed",params:{}};return p`
                <div class="card">
                    <div class="state-msg">
                        ${this._t(s.key,s.params)}
                    </div>
                </div>
            `}if(this._state==="loading"||!this._model)return p`
                <div class="card">
                    <div class="state-msg">
                        <div class="spinner"></div>
                        <span>${this._t("loading")}</span>
                    </div>
                </div>
            `;let t=this._model,e=this._stateValue(t.version),n=this._stateValue(t.clashMode),i=this._config.show_test_all!==!1&&(t.groups.length>0||t.standalone.length>0);return p`
            <div class="card">
                <div class="header">
                    <h2>${this._config.title}</h2>
                    <div class="meta">
                        ${e?p`<span>${e}</span>`:""}
                        ${n?p`<span> · ${n}</span>`:""}
                    </div>
                    ${i?p`
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

                ${this._config.show_speeds!==!1?p`<div class="speeds">
                          ${this._speedTile("up","mdi:arrow-up-bold",this._t("speedUp"),t.uplink)}
                          ${this._speedTile("down","mdi:arrow-down-bold",this._t("speedDown"),t.downlink)}
                      </div>`:""}

                ${this._config.show_chart!==!1?this._renderChart():""}

                ${this._config.show_totals!==!1?p`<div class="totals">
                          ${this._totalChip("mdi:arrow-up",this._formatBytes(t.uplinkTotal))}
                          ${this._totalChip("mdi:arrow-down",this._formatBytes(t.downlinkTotal))}
                          ${this._totalChip("mdi:memory",this._formatBytes(t.memory))}
                          ${this._totalChip("mdi:lan-connect",this._stateValue(t.connectionsIn))}
                      </div>`:""}

                ${this._config.show_groups!==!1?p`
                          ${t.groups.map(s=>this._renderGroup(s))}
                          ${t.standalone.length?this._renderStandalone(t.standalone):""}
                      `:""}

                ${this._renderConnections()}

                ${this._fallbackNote?p`<div class="fallback-note">${this._t(this._fallbackNote.key,this._fallbackNote.params)}</div>`:""}
                <div class="footer">sing-box panel · v${re}</div>
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
        `}_renderStandaloneNode(t){let e=this._ping(t),n=!!this._testing[t.tag];return p`
            <div class="node">
                <span class="node-name standalone">${t.tag}</span>
                ${e!==null?p`<span class="ping ${this._pingClass(e)}">${this._pingText(e)}</span>`:""}
                <button
                    class="node-ping"
                    title=${this._t("pingTitle",{tag:t.tag})}
                    ?disabled=${n}
                    @click=${()=>this._pingNode(t.tag,t.pingEntity)}
                >
                    <ha-icon icon="mdi:radar"></ha-icon>
                </button>
            </div>
        `}_speedTile(t,e,n,i){let{value:s,unit:r}=this._formatSpeed(i);return p`
            <div class="tile ${t}">
                <ha-icon icon=${e}></ha-icon>
                <div class="tile-body">
                    <div class="tile-label">${n}</div>
                    <div class="tile-value">${s}<span class="unit">${r}</span></div>
                </div>
            </div>
        `}_totalChip(t,e){return p`
            <span class="chip-stat">
                <ha-icon icon=${t}></ha-icon>
                <b>${e}</b>
            </span>
        `}_renderGroup(t){let e=this._groupCurrent(t),n=!!this._testing[t.tag];return p`
            <div class="group">
                <div class="group-head">
                    <span class="group-name">${t.tag}</span>
                    <span class="group-current">
                        ${e?p`→ <b>${e}</b>`:""}
                    </span>
                    <button
                        class="test-btn"
                        ?disabled=${n}
                        @click=${()=>this._testGroup(t)}
                    >
                        <ha-icon icon="mdi:flash-outline"></ha-icon>
                        ${n?this._t("testing"):this._t("test")}
                    </button>
                </div>
                <div class="nodes">
                    ${t.options.map(i=>this._renderNode(t,i,e))}
                </div>
            </div>
        `}_renderNode(t,e,n){let i=this._ping(e),s=e.tag===n,r=!!this._testing[e.tag];return p`
            <div class="node ${s?"active":""}">
                <button
                    class="node-select"
                    title=${this._t("selectTitle",{tag:e.tag})}
                    @click=${()=>this._selectNode(t.tag,e.tag,t.entityId)}
                >
                    <span class="node-name">${e.tag}</span>
                    ${i!==null?p`<span class="ping ${this._pingClass(i)}">${this._pingText(i)}</span>`:""}
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
        `}};customElements.get("singbox-panel-card")||customElements.define("singbox-panel-card",ht);window.customCards=window.customCards||[];window.customCards.some(o=>o.type==="singbox-panel-card")||window.customCards.push({type:"singbox-panel-card",name:"Sing-box Panel",description:"\u041F\u0430\u043D\u0435\u043B\u044C \u043C\u043E\u043D\u0438\u0442\u043E\u0440\u0438\u043D\u0433\u0430 \u0438 \u0443\u043F\u0440\u0430\u0432\u043B\u0435\u043D\u0438\u044F \u043F\u0440\u043E\u043A\u0441\u0438 sing-box",preview:!1});
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
