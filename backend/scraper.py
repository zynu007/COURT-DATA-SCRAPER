from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time
import re
import logging
import json
from typing import Dict, List, Optional, Tuple
from config import Config
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DelhiHighCourtScraper:
    """
    Fixed scraper for Delhi High Court case data with proper document extraction.
    """
    
    def __init__(self, timeout: int = 90):
        self.timeout = timeout
        self.base_url = "https://delhihighcourt.nic.in"
        self.case_status_url = f"{self.base_url}/app/get-case-type-status"
        self.captcha_validate_url = f"{self.base_url}/app/validateCaptcha"
        
    def _get_case_types(self, page) -> Dict[str, str]:
        """
        Scrape available case types from the dropdown.
        Returns: Dict mapping display names to form values.
        """
        try:
            page.wait_for_selector('select[name="case_type"]', timeout=self.timeout * 1000)
            case_types = {}
            options = page.query_selector_all('select[name="case_type"] option')
            for option in options:
                value = option.get_attribute('value')
                text = option.text_content().strip()
                if value and text and value != "":
                    case_types[text] = value
            logger.info(f"Found {len(case_types)} case types.")
            return case_types
        except Exception as e:
            logger.error(f"Error extracting case types: {str(e)}")
            return {}
    
    def _find_form_fields(self, page) -> Dict[str, str]:
        """
        Dynamically find form field selectors by inspecting the actual form structure.
        """
        form_fields = {}
        
        try:            
            # Case type field - a select dropdown
            case_type_selectors = [
                'select[name="case_type"]',
                'select[name="caseType"]', 
                'select[id*="case_type"]',
                'select[id*="caseType"]'
            ]
            
            for selector in case_type_selectors:
                if page.query_selector(selector):
                    form_fields['case_type'] = selector
                    logger.info(f"Found case type field: {selector}")
                    break
            
            # Case number field
            case_number_selectors = [
                'input[name="case_number"]',
                'input[name="caseNumber"]',
                'input[name="case_no"]',
                'input[name="caseNo"]',
                'input[id*="case_number"]',
                'input[id*="caseNumber"]',
                'input[placeholder*="Case Number"]',
                'input[placeholder*="case number"]'
            ]
            
            for selector in case_number_selectors:
                if page.query_selector(selector):
                    form_fields['case_number'] = selector
                    logger.info(f"Found case number field: {selector}")
                    break
            
            # Filing year field - could be input or select
            filing_year_selectors = [
                'input[name="filing_year"]',
                'input[name="filingYear"]',
                'input[name="case_year"]',
                'input[name="caseYear"]',
                'input[name="year"]',
                'select[name="filing_year"]',
                'select[name="filingYear"]',
                'select[name="case_year"]',
                'select[name="caseYear"]',
                'select[name="year"]',
                'input[id*="filing_year"]',
                'input[id*="filingYear"]',
                'input[id*="case_year"]',
                'input[id*="year"]',
                'input[placeholder*="Year"]',
                'input[placeholder*="Filing Year"]'
            ]
            
            for selector in filing_year_selectors:
                if page.query_selector(selector):
                    form_fields['filing_year'] = selector
                    logger.info(f"Found filing year field: {selector}")
                    break
            
            # CAPTCHA field
            captcha_selectors = [
                'input[name="captchaInput"]',
                'input[name="captcha"]',
                'input[name="captcha_input"]',
                'input[id*="captcha"]',
                'input[placeholder*="captcha"]',
                'input[placeholder*="Captcha"]'
            ]
            
            for selector in captcha_selectors:
                if page.query_selector(selector):
                    form_fields['captcha'] = selector
                    logger.info(f"Found captcha field: {selector}")
                    break
            
            return form_fields
            
        except Exception as e:
            logger.error(f"Error finding form fields: {str(e)}")
            return {}
    
    def _debug_form_structure(self, page):
        """
        Debug function to inspect the actual form structure
        """
        try:
            # Get all input and select elements
            inputs = page.query_selector_all('input, select')
            logger.info("=== FORM STRUCTURE DEBUG ===")
            for i, element in enumerate(inputs):
                tag_name = element.evaluate('el => el.tagName')
                name_attr = element.get_attribute('name') or 'NO_NAME'
                id_attr = element.get_attribute('id') or 'NO_ID'
                placeholder = element.get_attribute('placeholder') or 'NO_PLACEHOLDER'
                input_type = element.get_attribute('type') or 'NO_TYPE'
                
                logger.info(f"Element {i}: <{tag_name}> name='{name_attr}' id='{id_attr}' type='{input_type}' placeholder='{placeholder}'")
            
            logger.info("=== END FORM STRUCTURE DEBUG ===")
            
        except Exception as e:
            logger.error(f"Error during form structure debug: {str(e)}")
            
    def _handle_captcha(self, page) -> Optional[str]:
        try:
            # Wait for CAPTCHA to load
            captcha_span = page.wait_for_selector('span#captcha-code', timeout=10000)
            if captcha_span:
                captcha_solution = captcha_span.text_content().strip()
                logger.info(f"CAPTCHA text found: {captcha_solution}")
                
                # Get CSRF token from the page
                csrf_token = self._get_csrf_token(page)
                if not csrf_token:
                    logger.warning("CSRF token not found")
                    return None
                
                # Validate CAPTCHA via API with proper headers and data
                try:
                    # Make the validation request using page.request to maintain session
                    response = page.request.post(
                        self.captcha_validate_url,
                        headers={
                            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                            'X-Requested-With': 'XMLHttpRequest',
                            'Accept': '*/*',
                            'Referer': self.case_status_url
                        },
                        data=f"_token={csrf_token}&captchaInput={captcha_solution}"
                    )
                    
                    if response.ok:
                        try:
                            result = response.json()
                            if result.get("success", False):
                                logger.info("CAPTCHA validation successful")
                                return captcha_solution
                            else:
                                logger.warning(f"CAPTCHA validation failed: {result}")
                                return None
                        except json.JSONDecodeError:
                            logger.warning("Invalid JSON response from CAPTCHA validation")
                            return captcha_solution  # Try anyway
                    else:
                        logger.warning(f"CAPTCHA validation request failed with status: {response.status}")
                        return captcha_solution  # Try anyway
                        
                except Exception as e:
                    logger.error(f"CAPTCHA validation request error: {str(e)}")
                    return captcha_solution  # Try anyway
                    
            else:
                logger.warning("CAPTCHA span not found")
                return None
        except Exception as e:
            logger.error(f"Error handling CAPTCHA: {str(e)}")
            return None
    
    def _get_csrf_token(self, page) -> str:
        try:
            # First try meta tag
            token_element = page.query_selector('meta[name="csrf-token"]')
            if token_element:
                token = token_element.get_attribute('content')
                if token:
                    return token
            
            # Try to find token in input field
            token_input = page.query_selector('input[name="_token"]')
            if token_input:
                token = token_input.get_attribute('value')
                if token:
                    return token
            
            # Try to extract from page content using regex
            page_content = page.content()
            token_match = re.search(r'<meta name="csrf-token" content="([^"]+)"', page_content)
            if token_match:
                return token_match.group(1)
                
            # Try to find in script tags
            token_match = re.search(r'"_token"\s*:\s*"([^"]+)"', page_content)
            if token_match:
                return token_match.group(1)
            
            logger.warning("CSRF token not found in any location")
            return ""
        except Exception as e:
            logger.error(f"Error getting CSRF token: {str(e)}")
            return ""
        

    def _extract_direct_pdf_from_case_page(self, case_page_url: str) -> Optional[str]:
        """
        Extract direct PDF URL from case details page by finding the first PDF link
        """
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                logger.info(f"Loading case page: {case_page_url}")
                page.goto(case_page_url, timeout=30000)
                page.wait_for_load_state('networkidle', timeout=15000)
                
                # Wait for the table to load completely
                page.wait_for_selector('table', timeout=10000)
                
                # Look for PDF links in the specific pattern used by Delhi High Court
                # These links have showlogo in the href and are inside table rows
                pdf_selectors = [
                    'table a[href*="showlogo"]',
                    'tbody a[href*="showlogo"]',
                    'tr a[href*="showlogo"]',
                    'a[href*="showlogo"][href*=".pdf"]'
                ]
                
                pdf_link = None
                for selector in pdf_selectors:
                    links = page.query_selector_all(selector)
                    if links:
                        # Get the first link (latest order)
                        pdf_link = links[0]
                        logger.info(f"Found PDF link using selector: {selector}")
                        break
                
                if pdf_link:
                    href = pdf_link.get_attribute('href')
                    if href:
                        # Construct full URL if needed
                        if href.startswith('/'):
                            pdf_url = f"{self.base_url}{href}"
                        elif not href.startswith('http'):
                            pdf_url = f"{self.base_url}/{href}"
                        else:
                            pdf_url = href
                        
                        browser.close()
                        logger.info(f"Found direct PDF URL: {pdf_url}")
                        return pdf_url
                
                # Additional fallback: look for any links with showlogo pattern in the page content
                page_content = page.content()
                import re
                pdf_pattern = r'href=["\']([^"\']*showlogo[^"\']*\.pdf[^"\']*)["\']'
                pdf_matches = re.findall(pdf_pattern, page_content)
                
                if pdf_matches:
                    first_pdf = pdf_matches[0]
                    if first_pdf.startswith('/'):
                        pdf_url = f"{self.base_url}{first_pdf}"
                    elif not first_pdf.startswith('http'):
                        pdf_url = f"{self.base_url}/{first_pdf}"
                    else:
                        pdf_url = first_pdf
                    
                    browser.close()
                    logger.info(f"Found PDF URL via regex: {pdf_url}")
                    return pdf_url
                
                browser.close()
                logger.warning(f"No PDF URL found on page: {case_page_url}")
                return None
                    
        except Exception as e:
            logger.error(f"Error extracting PDF URL from {case_page_url}: {str(e)}")
            return None
               

    def _extract_case_data_from_api(self, api_response: Dict) -> Dict:
        case_data = {
            'parties_names': '',
            'filing_date': '',
            'next_hearing_date': '',
            'case_status': '',
            'documents': []
        }
        
        try:
            # Check if response has data
            if not api_response.get('data'):
                logger.warning("No data in API response")
                return case_data
            
            data_items = api_response['data']
            if not data_items:
                logger.warning("Empty data array in API response")
                return case_data
            
            logger.info(f"Processing {len(data_items)} data items from API response")
            
            # Process each case record - we only want the first/latest one
            latest_item = data_items[0]  # Get the first item which should be the latest
            
            # Extract parties names and clean HTML tags
            if 'pet' in latest_item and latest_item['pet']:
                parties_text = latest_item['pet']
                parties_text = re.sub(r'<[^>]+>', '', parties_text)
                parties_text = re.sub(r'&nbsp;', ' ', parties_text)
                parties_text = re.sub(r'\s+', ' ', parties_text).strip()
                case_data['parties_names'] = parties_text
            
            # Extract case type and details
            if 'ctype' in latest_item and latest_item['ctype']:
                case_data['case_status'] = re.sub(r'<[^>]+>', '', latest_item['ctype']).strip()
            
            # Extract and clean order date
            order_date = ''
            if 'orderdate' in latest_item and latest_item['orderdate']:
                date_text = latest_item['orderdate']
                date_text = re.sub(r'<[^>]+>', '', date_text)
                date_text = re.sub(r'&nbsp;', ' ', date_text)
                date_text = re.sub(r'\s+', ' ', date_text).strip()
                order_date = date_text
                case_data['filing_date'] = date_text
            
            # Extract case details URL from ctype field - FIXED VERSION
            if 'ctype' in latest_item and latest_item['ctype']:
                ctype_html = latest_item['ctype']
                logger.info(f"Raw ctype HTML: {ctype_html}")
                
                # More specific regex to extract only the href value
                # This pattern looks for href= followed by the URL until the next space or quote
                href_patterns = [
                    r'href=["\']([^"\']*case-type-status-details[^"\']*)["\']',  # Standard quoted href
                    r'href=([^\s>]*case-type-status-details[^\s>]*)',  # Unquoted href
                    r'href=["\']?([^"\'\s>]*eyJ[^"\'\s>]*)["\']?'  # Look for the encrypted token pattern
                ]
                
                case_details_url = None
                for pattern in href_patterns:
                    href_match = re.search(pattern, ctype_html, re.IGNORECASE)
                    if href_match:
                        case_details_url = href_match.group(1)
                        logger.info(f"Extracted URL using pattern {pattern}: {case_details_url}")
                        break
                
                if case_details_url:
                    # Clean up HTML entities and decode URL if needed
                    import urllib.parse
                    case_details_url = urllib.parse.unquote(case_details_url)
                    
                    # Remove any trailing HTML that might have been captured
                    case_details_url = re.sub(r'[\'"].*$', '', case_details_url)
                    case_details_url = case_details_url.split()[0]  # Take only the first part before any space
                    
                    if not case_details_url.startswith('http'):
                        case_details_url = f"{self.base_url}{case_details_url}"
                    
                    logger.info(f"Final cleaned URL: {case_details_url}")
                    
                    # Clean the case reference
                    clean_case_ref = re.sub(r'<[^>]+>', '', latest_item.get('ctype', '')).strip()
                    clean_case_ref = re.sub(r'&nbsp;', ' ', clean_case_ref)
                    clean_case_ref = re.sub(r'\s+', ' ', clean_case_ref).strip()
                    
                    # Extract direct PDF URL from the case details page
                    logger.info(f"Extracting PDF URL from: {case_details_url}")
                    direct_pdf_url = self._extract_direct_pdf_from_case_page(case_details_url)
                    
                    if direct_pdf_url:
                        # We found a direct PDF link
                        case_data['documents'].append({
                            'title': f"Latest Order - {clean_case_ref}",
                            'url': direct_pdf_url,
                            'type': 'order',
                            'date': order_date,
                            'case_ref': clean_case_ref,
                            'is_direct_pdf': True
                        })
                        logger.info(f"Added direct PDF document: {direct_pdf_url}")
                    else:
                        # Fallback to case details page
                        case_data['documents'].append({
                            'title': f"Case Details - {clean_case_ref}",
                            'url': case_details_url,
                            'type': 'case_details',
                            'date': order_date,
                            'case_ref': clean_case_ref,
                            'is_direct_pdf': False
                        })
                        logger.info(f"Added case details page: {case_details_url}")
                else:
                    logger.warning("No valid case details URL found in ctype field")
            
            return case_data
            
        except Exception as e:
            logger.error(f"Error extracting case data from API: {str(e)}")
            return case_data



    def _get_latest_order_only(self, api_response: Dict) -> List[Dict]:
        """
        Extract only the latest order document from API response
        """
        documents = []
        latest_order = None
        latest_date = None
        
        try:
            if not api_response.get('data'):
                return documents
            
            for item in api_response['data']:
                # Extract order date
                order_date_str = ''
                if 'orderdate' in item and item['orderdate']:
                    date_text = item['orderdate']
                    date_text = re.sub(r'<[^>]+>', '', date_text)
                    date_text = re.sub(r'&nbsp;', ' ', date_text)
                    date_text = re.sub(r'\s+', ' ', date_text).strip()
                    order_date_str = date_text
                
                # Parse date for comparison
                try:
                    parsed_date = datetime.strptime(order_date_str, '%d/%m/%Y') if order_date_str else datetime.min
                except:
                    parsed_date = datetime.min
                
                # Extract PDF URL from ctype field
                if 'ctype' in item and item['ctype']:
                    ctype_html = item['ctype']
                    href_match = re.search(r'href=["\']([^"\']+)["\']', ctype_html, re.IGNORECASE)
                    
                    if href_match:
                        case_url = href_match.group(1)
                        if not case_url.startswith('http'):
                            case_url = f"{self.base_url}{case_url}"
                        
                        # Get direct PDF URL
                        direct_pdf_url = self._extract_direct_pdf_from_case_page(case_url)
                        
                        if direct_pdf_url and (latest_date is None or parsed_date > latest_date):
                            latest_date = parsed_date
                            latest_order = {
                                'title': "Latest Order",
                                'url': direct_pdf_url,
                                'type': 'order',
                                'date': order_date_str,
                                'case_ref': re.sub(r'&nbsp;', ' ', re.sub(r'<[^>]+>', '', item.get('ctype', ''))).strip()
                            }
            
            if latest_order:
                documents.append(latest_order)
                logger.info(f"Found latest order: {latest_order['url']}")
        
        except Exception as e:
            logger.error(f"Error getting latest order: {str(e)}")
        
        return documents


    def _extract_direct_pdf_from_case_page(self, case_page_url: str) -> Optional[str]:
        """
        Extract direct PDF URL from case details page by clicking on the case link
        """
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(case_page_url, timeout=30000)
                page.wait_for_load_state('networkidle', timeout=10000)
                
                # Look for clickable case links in the table
                case_links = page.query_selector_all('a[href*="showlogo"], table a[href*=".pdf"]')
                
                if case_links:
                    # Get the first (latest) case link
                    first_link = case_links[0]
                    pdf_href = first_link.get_attribute('href')
                    
                    if pdf_href:
                        if pdf_href.startswith('/'):
                            pdf_url = f"{self.base_url}{pdf_href}"
                        elif not pdf_href.startswith('http'):
                            pdf_url = f"{self.base_url}/{pdf_href}"
                        else:
                            pdf_url = pdf_href
                        
                        browser.close()
                        logger.info(f"Extracted direct PDF URL: {pdf_url}")
                        return pdf_url
                
                # Alternative: Look for any PDF links
                pdf_links = page.query_selector_all('a[href$=".pdf"], a[href*=".pdf"], a[href*="showlogo"]')
                for link in pdf_links:
                    href = link.get_attribute('href')
                    if href and ('showlogo' in href or '.pdf' in href):
                        pdf_url = href if href.startswith('http') else f"{self.base_url}{href}"
                        browser.close()
                        logger.info(f"Found PDF link: {pdf_url}")
                        return pdf_url
                
                browser.close()
                logger.warning(f"No direct PDF URL found on page: {case_page_url}")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting direct PDF URL from {case_page_url}: {str(e)}")
            return None
    
    def search_case(self, case_type: str, case_number: str, filing_year: int) -> Tuple[bool, Dict, str]:
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(
                        headless=True,
                        args=['--no-sandbox', '--disable-dev-shm-usage']
                    )
                    
                    context = browser.new_context(
                        user_agent='Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Mobile Safari/537.36',
                        extra_http_headers={
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                            'Accept-Language': 'en-US,en;q=0.9,ml-IN;q=0.8,ml;q=0.7',
                            'Accept-Encoding': 'gzip, deflate, br, zstd',
                            'DNT': '1',
                            'Sec-Ch-Ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
                            'Sec-Ch-Ua-Mobile': '?1',
                            'Sec-Ch-Ua-Platform': '"Android"',
                            'Sec-Fetch-Dest': 'document',
                            'Sec-Fetch-Mode': 'navigate',
                            'Sec-Fetch-Site': 'none',
                            'Sec-Fetch-User': '?1'
                        }
                    )
                    
                    page = context.new_page()
                    
                    logger.info(f"Attempt {attempt + 1}: Navigating to case status page")
                    page.goto(self.case_status_url, timeout=self.timeout * 1000)
                    
                    # Wait for page to load completely
                    page.wait_for_load_state('networkidle', timeout=30000)
                    
                    # Debug: Inspect the actual form structure
                    self._debug_form_structure(page)
                    
                    # Get available case types first
                    available_case_types = self._get_case_types(page)
                    
                    if not available_case_types:
                        # Use fallback case types
                        available_case_types = {
                            "Civil Writ Petition": "CWP",
                            "Criminal Appeal": "CRL.A.",
                            "Criminal Writ Petition": "CrWP",
                            "Regular First Appeal": "RFA",
                            "Bail Application": "BAIL APPLN."
                        }
                    
                    # Find matching case type
                    selected_case_type_value = None
                    for display_name, form_value in available_case_types.items():
                        if (case_type.lower() in display_name.lower() or 
                            display_name.lower() in case_type.lower() or
                            form_value.lower() == case_type.lower()):
                            selected_case_type_value = form_value
                            break
                    
                    if not selected_case_type_value:
                        # Try direct mapping
                        case_type_mapping = {
                            'CWP': 'CWP',
                            'CIVIL WRIT PETITION': 'CWP',
                            'CRL.A.': 'CRL.A.',
                            'CRIMINAL APPEAL': 'CRL.A.',
                            'CRWP': 'CrWP',
                            'CRIMINAL WRIT PETITION': 'CrWP',
                            'BAIL APPLN.': 'BAIL APPLN.',
                            'BAIL APPLICATION': 'BAIL APPLN.'
                        }
                        selected_case_type_value = case_type_mapping.get(case_type.upper(), case_type)
                    
                    # Find form fields dynamically
                    form_fields = self._find_form_fields(page)
                    
                    # Wait for form elements to be ready with more flexible timeout
                    try:
                        if form_fields.get('case_type'):
                            page.wait_for_selector(form_fields['case_type'], timeout=15000)
                        if form_fields.get('case_number'):
                            page.wait_for_selector(form_fields['case_number'], timeout=5000)
                        if form_fields.get('filing_year'):
                            page.wait_for_selector(form_fields['filing_year'], timeout=5000)
                    except Exception as e:
                        logger.warning(f"Some form elements not found: {str(e)}")
                    
                    # Handle CAPTCHA first
                    captcha_solution = self._handle_captcha(page)
                    if not captcha_solution:
                        logger.warning(f"CAPTCHA handling failed on attempt {attempt + 1}")
                        if attempt == max_retries - 1:
                            return False, {}, "CAPTCHA validation failed"
                        continue
                    
                    # Fill the form with error handling for each field
                    try:
                        # Fill case type
                        if form_fields.get('case_type'):
                            case_type_element = page.query_selector(form_fields['case_type'])
                            if case_type_element:
                                if case_type_element.evaluate('el => el.tagName').lower() == 'select':
                                    page.select_option(form_fields['case_type'], selected_case_type_value)
                                else:
                                    page.fill(form_fields['case_type'], selected_case_type_value)
                                logger.info(f"Case type filled: {selected_case_type_value}")
                            else:
                                logger.warning("Case type element not found")
                        else:
                            logger.warning("Case type selector not identified")
                        
                        # Fill case number
                        if form_fields.get('case_number'):
                            case_number_element = page.query_selector(form_fields['case_number'])
                            if case_number_element:
                                page.fill(form_fields['case_number'], case_number)
                                logger.info(f"Case number filled: {case_number}")
                            else:
                                logger.warning("Case number element not found")
                        else:
                            logger.warning("Case number selector not identified")
                        
                        # Fill filing year
                        if form_fields.get('filing_year'):
                            filing_year_element = page.query_selector(form_fields['filing_year'])
                            if filing_year_element:
                                if filing_year_element.evaluate('el => el.tagName').lower() == 'select':
                                    # Try to select the year from dropdown
                                    try:
                                        page.select_option(form_fields['filing_year'], str(filing_year))
                                        logger.info(f"Filing year selected from dropdown: {filing_year}")
                                    except Exception as e:
                                        logger.warning(f"Could not select year from dropdown: {str(e)}")
                                        page.fill(form_fields['filing_year'], str(filing_year))
                                else:
                                    page.fill(form_fields['filing_year'], str(filing_year))
                                    logger.info(f"Filing year filled: {filing_year}")
                            else:
                                logger.warning("Filing year element not found after identification")
                        else:
                            logger.warning("Filing year selector not identified - checking all possible fields")
                            
                            # Try alternative approach - fill any year-related field
                            year_filled = False
                            year_selectors = [
                                'input[name*="year"]', 'select[name*="year"]',
                                'input[id*="year"]', 'select[id*="year"]',
                                'input[placeholder*="Year" i]'
                            ]
                            
                            for selector in year_selectors:
                                elements = page.query_selector_all(selector)
                                for element in elements:
                                    try:
                                        if element.evaluate('el => el.tagName').lower() == 'select':
                                            page.select_option(selector, str(filing_year))
                                        else:
                                            page.fill(selector, str(filing_year))
                                        logger.info(f"Filing year filled using fallback selector {selector}: {filing_year}")
                                        year_filled = True
                                        break
                                    except Exception:
                                        continue
                                if year_filled:
                                    break
                            
                            if not year_filled:
                                logger.error("Could not find any filing year field")
                        
                        # Fill CAPTCHA
                        if form_fields.get('captcha'):
                            captcha_element = page.query_selector(form_fields['captcha'])
                            if captcha_element:
                                page.fill(form_fields['captcha'], captcha_solution)
                                logger.info("CAPTCHA filled successfully")
                            else:
                                logger.warning("CAPTCHA element not found")
                        else:
                            # Try fallback CAPTCHA selectors
                            captcha_filled = False
                            captcha_selectors = ['input[name*="captcha" i]', 'input[id*="captcha" i]']
                            for selector in captcha_selectors:
                                captcha_element = page.query_selector(selector)
                                if captcha_element:
                                    page.fill(selector, captcha_solution)
                                    logger.info(f"CAPTCHA filled using fallback selector: {selector}")
                                    captcha_filled = True
                                    break
                            
                            if not captcha_filled:
                                logger.warning("Could not find CAPTCHA input field")
                        
                        # Small delay to ensure form is ready
                        page.wait_for_timeout(2000)
                        
                    except Exception as e:
                        logger.error(f"Error filling form: {str(e)}")
                        # Don't continue to next attempt, try to proceed with form submission
                    
                    # Listen for the API response
                    api_response = None
                    
                    def handle_response(response):
                        nonlocal api_response
                        if ('get-case-type-status' in response.url and 
                            ('case_type=' in response.url or 'draw=' in response.url)):
                            try:
                                api_response = response.json()
                                logger.info("Captured API response successfully")
                            except Exception as e:
                                logger.error(f"Error parsing API response: {str(e)}")
                    
                    page.on("response", handle_response)
                    
                    # Try to submit the form
                    try:
                        # Look for submit button with multiple selectors
                        submit_selectors = [
                            'input[type="submit"]',
                            'button[type="submit"]', 
                            'button:has-text("Submit")',
                            'button:has-text("Search")',
                            'input[value*="Submit" i]',
                            'input[value*="Search" i]',
                            '.btn-primary',
                            '.btn-submit'
                        ]
                        
                        submit_button = None
                        for selector in submit_selectors:
                            submit_button = page.query_selector(selector)
                            if submit_button:
                                logger.info(f"Found submit button with selector: {selector}")
                                break
                        
                        if submit_button:
                            submit_button.click()
                            logger.info("Form submitted successfully")
                        else:
                            logger.warning("Submit button not found, trying form submission via Enter key")
                            # Try to trigger form submission via Enter key
                            if form_fields.get('captcha'):
                                captcha_element = page.query_selector(form_fields['captcha'])
                                if captcha_element:
                                    captcha_element.press('Enter')
                            
                    except Exception as e:
                        logger.error(f"Error submitting form: {str(e)}")
                    
                    # Wait for API response with longer timeout
                    start_time = time.time()
                    while api_response is None and (time.time() - start_time) < 45:
                        page.wait_for_timeout(1000)
                        
                        # Check if we've been redirected to results page
                        current_url = page.url
                        if 'case-type-status-details' in current_url or 'Orders' in page.content():
                            logger.info("Detected results page, trying to extract data")
                            break
                    
                    # Try to extract documents from the results page if available
                    results_documents = []
                    try:
                        # Check if we're on a results page
                        if 'case-type-status-details' in page.url or page.query_selector('table'):
                            results_documents = self._extract_documents_from_results_page(page)
                            logger.info(f"Extracted {len(results_documents)} documents from results page")
                    except Exception as e:
                        logger.warning(f"Error extracting from results page: {str(e)}")
                    
                    # If no API response, try direct API call with corrected parameters
                    if api_response is None:
                        logger.warning("No API response captured, trying direct API call")
                        
                        # Get CSRF token for API call
                        csrf_token = self._get_csrf_token(page)
                        
                        # Construct the API URL based on the actual network request pattern
                        api_params = {
                            'draw': '1',
                            'start': '0',
                            'length': '50',
                            'case_type': selected_case_type_value,
                            'case_number': case_number,
                            'case_year': str(filing_year),  # Note: using case_year, not filing_year
                            '_': str(int(time.time() * 1000))
                        }
                        
                        # Add DataTables parameters
                        for i in range(4):
                            api_params[f'columns[{i}][searchable]'] = 'true'
                            api_params[f'columns[{i}][orderable]'] = 'true' if i > 0 else 'false'
                            api_params[f'columns[{i}][search][value]'] = ''
                            api_params[f'columns[{i}][search][regex]'] = 'false'
                        
                        api_params['columns[0][data]'] = 'DT_RowIndex'
                        api_params['columns[0][name]'] = 'DT_RowIndex'
                        api_params['columns[1][data]'] = 'ctype'
                        api_params['columns[1][name]'] = 'ctype'
                        api_params['columns[2][data]'] = 'pet'
                        api_params['columns[2][name]'] = 'pet'
                        api_params['columns[3][data]'] = 'orderdate'
                        api_params['columns[3][name]'] = 'orderdate'
                        
                        api_params['order[0][column]'] = '0'
                        api_params['order[0][dir]'] = 'asc'
                        api_params['order[0][name]'] = 'DT_RowIndex'
                        api_params['search[value]'] = ''
                        api_params['search[regex]'] = 'false'
                        
                        # Build query string
                        query_string = '&'.join([f"{k}={v}" for k, v in api_params.items()])
                        api_url = f"{self.case_status_url}?{query_string}"
                        
                        try:
                            # Include proper headers for the API call
                            response = page.request.get(
                                api_url,
                                headers={
                                    'X-Requested-With': 'XMLHttpRequest',
                                    'Accept': 'application/json, text/javascript, */*; q=0.01',
                                    'Referer': self.case_status_url,
                                    'X-CSRF-TOKEN': csrf_token
                                }
                            )
                            
                            if response.ok:
                                response_text = response.text()
                                if response_text.strip():
                                    api_response = response.json()
                                    logger.info("Direct API call successful")
                                else:
                                    logger.error("Empty response from direct API call")
                            else:
                                logger.error(f"Direct API call failed: {response.status} - {response.text()}")
                        except json.JSONDecodeError as e:
                            logger.error(f"JSON decode error from API response: {str(e)}")
                        except Exception as e:
                            logger.error(f"Direct API call error: {str(e)}")
                    
                    browser.close()
                    
                    if api_response:
                        case_data = self._extract_case_data_from_api(api_response)
                        case_data['raw_html'] = json.dumps(api_response)
                        # Add documents from results page if any were found
                        """if results_documents:
                            case_data['documents'].extend(results_documents)
                            logger.info(f"Added {len(results_documents)} documents from results page")"""
                        
                        # If still no documents, try to construct order URLs based on case info
                        if not case_data['documents'] and api_response.get('data'):
                            for item in api_response['data']:
                                if 'ctype' in item:
                                    case_ref = item['ctype']
                                    # Construct order URL based on the pattern seen in the official site
                                    order_url = f"{self.base_url}/app/case-type-status-details/{case_ref.replace(' ', '%20')}"
                                    
                                    # Clean the case_ref from HTML tags
                                    clean_case_ref = re.sub(r'<[^>]+>', '', item.get('ctype', '')).strip()
                                    clean_case_ref = re.sub(r'&nbsp;', ' ', clean_case_ref)
                                    clean_case_ref = re.sub(r'\s+', ' ', clean_case_ref).strip()

                                    case_data['documents'].append({
                                        'title': f"Orders for {clean_case_ref}",
                                        'url': order_url,
                                        'type': 'order',
                                        'date': item.get('orderdate', ''),
                                        'case_ref': clean_case_ref  # Now clean text
                                    })
                                    logger.info(f"Constructed order URL: {order_url}")
                        
                        case_data['raw_html'] = json.dumps(api_response)
                        case_data['search_params'] = {
                            'case_type': case_type,
                            'case_number': case_number,
                            'filing_year': filing_year
                        }
                        return True, case_data, ""
                    else:
                        logger.warning("No API response received")
                        return False, {}, "No data received from court API"
        
            except PlaywrightTimeoutError:
                logger.warning(f"Request timed out on attempt {attempt + 1}")
                time.sleep(5)
                if attempt == max_retries - 1:
                    return False, {}, "Request timed out - court website may be slow or down"
            except Exception as e:
                logger.error(f"Scraping error on attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    return False, {}, f"Scraping failed: {str(e)}"
                time.sleep(5)
        
        return False, {}, "All attempts failed"
        
    def get_available_case_types(self) -> Dict[str, str]:
        """
        Get all available case types from the court website.
        """
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(self.case_status_url, timeout=self.timeout * 1000)
                
                case_types = self._get_case_types(page)
                browser.close()
                
                if not case_types:
                    # Fallback case types
                    case_types = {
                        "Civil Writ Petition": "CWP",
                        "Criminal Appeal": "CRL.A.",
                        "Criminal Writ Petition": "CrWP", 
                        "Regular First Appeal": "RFA",
                        "Civil Miscellaneous Main": "CM(M)",
                        "Criminal Revision": "CrR",
                        "Bail Application": "BAIL APPLN."
                    }
                
                return case_types
        except Exception as e:
            logger.error(f"Error getting case types: {str(e)}")
            return {
                "Civil Writ Petition": "CWP",
                "Criminal Appeal": "CRL.A.",
                "Criminal Writ Petition": "CrWP", 
                "Regular First Appeal": "RFA",
                "Civil Miscellaneous Main": "CM(M)",
                "Bail Application": "BAIL APPLN."
            }