"""SmartDeal AI v3 — user-facing Streamlit application powered by LangGraph."""
import os
from dotenv import load_dotenv
load_dotenv()
import streamlit as st
# Streamlit Community Cloud stores keys in st.secrets, not necessarily os.environ.
# Copy only known backend settings into this server process before importing tools.
for secret_name in ('SERPAPI_KEY','KEENABLE_API_KEY','SUPABASE_URL','SUPABASE_SECRET_KEY','OLLAMA_MODEL','OLLAMA_URL','CACHE_HOURS'):
    try:
        if not os.getenv(secret_name) and secret_name in st.secrets:
            os.environ[secret_name] = str(st.secrets[secret_name])
    except (FileNotFoundError, KeyError):
        pass
import pandas as pd
from urllib.parse import urlparse
from agent.graph import graph
from agent.repository import get_store
from smartdeal.engine import thanksgiving_deals, valid_url

st.set_page_config(page_title='SmartDeal AI | Smart purchase decisions',page_icon='🛍️',layout='wide')
st.title('🛍️ SmartDeal AI')
st.subheader('Find your next great deal')
st.caption('Search products, explore offers, and compare stores with confidence.')
with st.sidebar:
    st.header('Refine your search')
    live=bool(os.getenv('SERPAPI_KEY', '').strip())
    st.caption('Product data: Live Google Shopping')
    priority=st.selectbox('Shopping priority',['balanced','price','protection','returns'],format_func=lambda x:{'balanced':'Best overall','price':'Lowest listed price','protection':'Warranty and protection','returns':'Return flexibility'}[x])
    location=st.text_input('Shopping location','United States')
    budget=st.number_input('Maximum listed price ($, 0 = any)',min_value=0.,value=0.,step=10.)
    minimum=st.slider('Minimum review rating',0.,5.,0.,0.5)
    refresh=st.checkbox('Refresh prices (costs search credit)',False)
    with st.expander('Advanced options'):
        keenable=st.checkbox('Research policy pages via Keenable',False,help='Optional independent web-search evidence. Does not verify listing-specific coverage.')
        ollama=st.checkbox('Ask local Qwen3 for a second explanation',False)
        st.caption('Database: Supabase' if os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_SECRET_KEY') else 'Database: local SQLite')

if not live:
    st.error('Live search requires SERPAPI_KEY. Add it to Streamlit app Settings → Secrets, then restart the app.')

shop_tab, thanksgiving_tab=st.tabs(['🛍️ Shop', '🍂 Thanksgiving deals'])
with shop_tab:
    with st.form('shop'):
        search_col, category_col = st.columns([2, 1])
        with search_col:
            q=st.text_input('What are you looking for?','65 inch smart TV',placeholder='Search for a product, brand or model')
        with category_col:
            category=st.selectbox('Shop by section',['All categories','Groceries','Entertainment','Electronics','Automotive','Travel'],help='Adds a category term to your search; results are not strictly category-filtered.')
        submitted=st.form_submit_button('🔎 Find deals',type='primary',disabled=not live)
    st.caption('Sections refine product searches. Travel results are shopping products, not flights or hotel bookings.')
with thanksgiving_tab:
    st.write('Find Thanksgiving offers for a product or browse a broad holiday search.')
    st.caption('Only listings with a provider-reported reduction are ranked as deals. Promotions and prices must be verified with the seller.')
    with st.form('thanksgiving'):
        holiday_query=st.text_input('Product or category (optional)',placeholder='For example: TVs, kitchen appliances, toys')
        holiday_submitted=st.form_submit_button('🍂 Find Thanksgiving deals',type='primary',disabled=not live)
    st.caption('A new search may use a SerpApi credit. Results appear below the search tabs.')
if submitted or holiday_submitted:
    search_query=(q.strip() if submitted else holiday_query.strip())
    if search_query and category != 'All categories':
        if submitted:
            search_query=f'{search_query} {category.lower()}'
    if holiday_submitted:
        search_query=f'{search_query} thanksgiving deals'.strip()
    with st.spinner('Finding offers for you...'):
        state=graph.invoke({'query':search_query,'location':location,'mode':'live','priority':priority,'budget':budget or None,'min_rating':minimum,'refresh':refresh,'use_keenable':keenable,'use_ollama':ollama})
    st.session_state['run']=state
    st.session_state['holiday_search']=holiday_submitted
if 'run' in st.session_state:
    s=st.session_state['run']
    if s.get('error'):st.error(s['error'])
    else:
        if s.get('mode')=='demo':st.warning('SYNTHETIC DEMO: Products, listed prices, ratings and stores are fictional. Do not use these figures to shop.')
        else:st.caption('Live Google Shopping results · Verify the final price, seller and policies before purchasing.')
        for n in s.get('notes',[]):st.caption(n)
        offers=s.get('ranked',[])
        holiday=st.session_state.get('holiday_search',False)
        if holiday:
            offers=thanksgiving_deals(offers)
        st.subheader(f'{"🍂 Thanksgiving deals" if holiday else "🛍️ Shop results"} · {len(offers)} offers')
        if not offers:
            if holiday and s.get('ranked'):
                st.info('No results included a provider-reported discount. Try another search or check the Shop tab for regular offers.')
            elif s.get('offers'):
                st.warning('Results were found, but none matched your price and rating filters. Increase the budget or lower the minimum rating, then search again.')
            else:
                st.warning('No usable priced listings were returned. Try fewer search terms, another section or location, or refresh prices. Google Shopping does not support every type of product or service.')
        if offers:
            sort_order=st.selectbox('Sort results',['Largest reported discount' if holiday else 'Recommended','Price: low to high','Price: high to low'],key='sort_holiday' if holiday else 'sort_offers')
            shown=list(offers)
            if sort_order == 'Price: low to high':
                shown.sort(key=lambda o:o.price)
            elif sort_order == 'Price: high to low':
                shown.sort(key=lambda o:o.price,reverse=True)
            columns=st.columns(3)
            for i,o in enumerate(shown):
                with columns[i % 3]:
                    with st.container(border=True):
                        if isinstance(o.image, str) and valid_url(o.image):
                            st.image(o.image, width=150)
                        else:
                            st.caption('Image unavailable')
                        st.write(o.title)
                        st.markdown(f'### ${o.price:,.2f}')
                        if holiday:
                            st.caption(f'{o.discount_pct:g}% off reported price of ${o.old_price:,.2f} · verify with seller')
                        st.caption(o.merchant)
                        if o.rating is not None:
                            rating=f'⭐ {o.rating:g} / 5'
                            if o.reviews is not None:
                                rating+=f' · {o.reviews:,} reviews'
                            st.caption(rating)
                        else:
                            st.caption('Rating unavailable')
                        if o.url and valid_url(o.url):
                            host=(urlparse(o.url).hostname or '').lower()
                            label='View on Google Shopping' if host == 'google.com' or host.endswith('.google.com') or host == 'googleadservices.com' or host.endswith('.googleadservices.com') else 'View listing'
                            st.link_button(label, o.url)
                        else:
                            st.caption('Listing link unavailable')
            st.caption('Links may redirect. Confirm the seller and final price on the destination site.')
            data=[{'Title':o.title,'Retailer':o.merchant,'Price':o.price,'Rating':o.rating,'Reviews':o.reviews,'Link':o.url} for o in shown]
            with st.expander('View results as a table or download'):
                st.dataframe(pd.DataFrame(data),hide_index=True,use_container_width=True)
                st.download_button('Download results (CSV)',pd.DataFrame(data).to_csv(index=False),'smartdeal-comparison.csv','text/csv')
        st.divider()
        st.subheader('🔍 Compare stores')
        if holiday:
            st.caption('Store comparison uses all matching search results, including listings without a reported discount.')
        # Comparison state is calculated from all matching offers, not just discounted ones.
        offers=s.get('ranked',[])
        groups=s.get('product_groups',{})
        if len(groups)>1:
            choice=st.selectbox('Compare the same product across retailers',list(groups),format_func=lambda k:f'{groups[k][0].title[:70]} • {len(groups[k])} offers')
            if choice!=s.get('selected_id'):
                from smartdeal.decision import compare_stores
                s['comparison']=compare_stores(offers,s['query'],priority=s['priority'],selected_product_id=choice)
                s['selected_id']=choice
                d=s['comparison']
                if not d.get('warning'):
                    s['explanation']=(f"Cheapest listing: {d['cheapest'].offer.merchant} ${d['cheapest'].offer.price:.2f}. "
                                      f"Best for your selected priority: {d['overall'].offer.merchant} ${d['overall'].offer.price:.2f}. "
                                      'Verify shipping, seller, membership and exact-item warranty terms before buying.')
        c=s.get('comparison',{})
        if c.get('warning'):
            st.warning(c['warning'])
        elif c:
            a,b,d=st.columns(3)
            a.metric('💲 Cheapest listing',c['cheapest'].offer.merchant,f'${c["cheapest"].offer.price:.2f}')
            b.metric('🏆 Best overall for your needs',c['overall'].offer.merchant,f'${c["overall"].offer.price:.2f}')
            d.metric('🛡️ Documented protection',c['protection'].offer.merchant if c.get('protection') else 'Not established')
        st.subheader('Decision explanation')
        st.write(s.get('explanation',''))
        if c and not c.get('warning'):
            st.subheader('Benefits by retailer')
            for d in c['rows']:
                with st.expander(f'{d.offer.merchant} • ${d.offer.price:.2f} • Decision score {d.score:.1f}/100'):
                    p=d.policy
                    st.write('**Return policy:** '+(p.returns_description if p else 'Unverified'))
                    st.write('**Warranty:** '+(p.warranty_description if p else 'Unverified'))
                    st.write('**Exceptions:** '+(p.exclusions if p else 'Verify seller-specific rules'))
                    if p:
                        for url in p.urls:st.markdown(f'[Official policy source]({url})')
                    st.caption('Category-level only; no individual listing eligibility has been verified.')
        if s.get('web_policy_evidence'):
            with st.expander('Optional Keenable web research (not independently verified)'):
                st.json(s['web_policy_evidence'])
        with st.expander('Price history for a matching product / retailer'):
            items=[o for o in offers if o.product_id]
            if items:
                selected=st.selectbox('Offer',items,format_func=lambda x:f'{x.merchant}: {x.title[:55]}')
                try:
                    rows=get_store().history(selected.product_id,selected.merchant)
                    if rows:
                        chart=pd.DataFrame(rows,columns=['checked_at','price'])
                        chart['checked_at']=pd.to_datetime(chart['checked_at'],utc=True)
                        st.line_chart(chart.set_index('checked_at')['price'])
                    else:st.caption('No historical observations yet.')
                except Exception as exc:st.warning(f'History unavailable: {type(exc).__name__}')
            else:st.caption('A shared exact product identifier is needed for price history.')
        st.caption('Retailer scores are illustrative. Missing shipping fees, tax, optional protection plans and membership costs are NOT assumed to be free. Rankings do not depend on affiliate commissions.')
else:
    st.info('Enter a product and compare live Google Shopping listings.' if live else 'Configure your SerpApi key to start searching live listings.')
