import pandas as pd
import streamlit as st
from streamlit_option_menu import option_menu
import easyocr
import mysql.connector
import cv2
import os
import matplotlib.pyplot as plt
import re


#mysql connection
mydb = mysql.connector.connect(host='localhost',user='root',password='Kavi@245',database='bizcard_data')
mycursor = mydb.cursor()

create_query = '''CREATE TABLE IF NOT EXISTS card_details
                   (card_holder TEXT,
                    company_name TEXT,
                    designation TEXT,
                    mobile_number VARCHAR(50),
                    email TEXT,
                    website TEXT,
                    area TEXT,
                    city TEXT,
                    state TEXT,
                    pin_code VARCHAR(10)
                    )'''
mycursor.execute(create_query)
mydb.commit()

def image_preview(image, res):
        for (bbox, text, prob) in res:
                (tl, tr, br, bl) = bbox
                tl = (int(tl[0]), int(tl[1]))
                tr = (int(tr[0]), int(tr[1]))
                br = (int(br[0]), int(br[1]))
                bl = (int(bl[0]), int(bl[1]))
                cv2.rectangle(image, tl, br, (255, 0, 0), 2)
                # cv2.putText(image, text, (tl[0], tl[1] - 10),
                #                 cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
        plt.rcParams['figure.figsize'] = (15, 15)
        plt.axis('off')
        plt.imshow(image)

# CONVERTING IMAGE TO BINARY TO UPLOAD TO SQL DATABASE
def img_to_binary(file):
        # Convert image data to binary format
        with open(file, 'rb') as file:
                binaryData = file.read()
        return binaryData

def get_data(res):
        for ind, i in enumerate(res):

                # To get WEBSITE_URL
                if "www " in i.lower() or "www." in i.lower():
                        data["website"].append(i)
                elif "WWW" in i:
                        data["website"] = res[4] + "." + res[5]

                # To get EMAIL ID
                elif "@" in i:
                    data["email"].append(i)

                # To get MOBILE NUMBER
                elif "-" in i:
                    data["mobile_number"].append(i)
                    if len(data["mobile_number"]) == 2:
                        data["mobile_number"] = " & ".join(data["mobile_number"])

                # To get COMPANY NAME
                elif ind == len(res) - 1:
                    #if res[ind-1].isdigit()==False:
                    data["company_name"].append(i)
 
                # To get CARD HOLDER NAME
                elif ind == 0:
                    data["card_holder"].append(i)

                # To get DESIGNATION
                elif ind == 1:
                    data["designation"].append(i)

                # To get AREA
                if re.findall('^[0-9].+, [a-zA-Z]+', i):
                    data["area"].append(i.split(',')[0])
                elif re.findall('[0-9] [a-zA-Z]+', i):
                    data["area"].append(i)

                # To get CITY NAME
                match1 = re.findall('.+St , ([a-zA-Z]+).+', i)
                match2 = re.findall('.+St,, ([a-zA-Z]+).+', i)
                match3 = re.findall('^[E].*', i)
                if match1:
                    data["city"].append(match1[0])
                elif match2:
                    data["city"].append(match2[0])
                elif match3:
                    data["city"].append(match3[0])

                # To get STATE
                state_match = re.findall('[a-zA-Z]{9} +[0-9]', i)
                if state_match:
                    data["state"].append(i[:9])
                elif re.findall('^[0-9].+, ([a-zA-Z]+);', i):
                    data["state"].append(i.split()[-1])
                if len(data["state"]) == 2:
                    data["state"].pop(0)

                # To get PINCODE
                if len(i) >= 6 and i.isdigit():
                    data["pin_code"].append(i)
                elif re.findall('[a-zA-Z]{9} +[0-9]', i):
                    data["pin_code"].append(i[10:])
                #st.write(i)
        df = pd.DataFrame(data)
        return df
        #st.write(df)


def insert_data():
        for index, row in df.iterrows():
                insert_query = '''
                        INSERT INTO card_details (card_holder, company_name, designation, mobile_number, 
                        email, website, area, city, state, pin_code)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)

                '''
                values = (
                        row['card_holder'],
                        row['company_name'],
                        row['designation'],
                        row['mobile_number'],
                        row['email'],
                        row['website'],
                        row['area'],
                        row['city'],
                        row['state'],
                        row['pin_code'],
                        #row['image']
                )
                mycursor.execute(insert_query,values)
        mydb.commit() 

def show_data():
        sql_query="select card_holder,company_name,designation,mobile_number,email,website,area,city,state,pin_code from card_details"
        mycursor.execute(sql_query)
        table=mycursor.fetchall()
        st.write(pd.DataFrame(table, columns=['Card Holder', 'Company Name', 'Designation','Mobile Number', 'Email', 'Website', 'Area', 'City',
                                                'State', 'Pin Code']))
      
def fetch_data():
    mycursor.execute('SELECT * FROM card_details')
    rows = mycursor.fetchall()
    column_names = [desc[0] for desc in mycursor.description]

    data_dict = {}
    for row in rows:
        data_dict[row[0]] = row[0:]

    return data_dict, column_names

# Function to update data in PostgreSQL
def update_data(selected_option, updated_values, column_names):
    update_query = f"UPDATE card_details SET {', '.join([f'{column_name} = %s' for column_name in column_names])} WHERE card_holder = %s"
    mycursor.execute(update_query, updated_values + [selected_option])
    mydb.commit()

def delete_data():
        delete_query = "DELETE FROM card_details WHERE card_holder = %s"
        mycursor.execute(delete_query, [selected_option])
        mydb.commit()


st.markdown("<h1 style='text-align: center; color: red;'>BizCardX: Extracting Business Card Data with OCR</h1>",
            unsafe_allow_html=True)

selected = option_menu(None, ["Extract","Modify"],
                       icons=["cloud-upload","pencil-square"],
                       default_index=0,
                       orientation="horizontal",
                       styles={"nav-link": {"font-size": "35px", "text-align": "centre", "margin": "-2px", "--hover-color": "#0c457d"},
                               "icon": {"font-size": "35px"},
                               "container" : {"max-width": "6000px"},
                               "nav-link-selected": {"background-color": "#6495ED"}})


#easyocr reader
reader = easyocr.Reader(['en'])
if selected == "Extract":
        uploaded_card = st.file_uploader("upload here", label_visibility="collapsed", type=["png", "jpeg", "jpg"])

        if uploaded_card is not None:
                uploaded_cards_dir = os.path.join(os.getcwd(), "uploaded_cards")
                os.makedirs(uploaded_cards_dir, exist_ok=True)  # Create the directory if it doesn't exist
                with open(os.path.join(uploaded_cards_dir, uploaded_card.name), "wb") as f:
                        f.write(uploaded_card.getbuffer())
                
                
                st.set_option('deprecation.showPyplotGlobalUse', False)
                saved_img = os.getcwd() + "\\" + "uploaded_cards" + "\\" + uploaded_card.name
                image = cv2.imread(saved_img)
                res = reader.readtext(saved_img)
                st.markdown("### Image Processed and Data Extracted")
                st.pyplot(image_preview(image, res))

                saved_img = os.getcwd() + "\\" + "uploaded_cards" + "\\" + uploaded_card.name
                result = reader.readtext(saved_img, detail=0, paragraph=False)

                data = {"card_holder": [],
                        "company_name": [],
                        "designation": [],
                        "mobile_number": [],
                        "email": [],
                        "website": [],
                        "area": [],
                        "city": [],
                        "state": [],
                        "pin_code": [],
                        "image": img_to_binary(saved_img)
                        }
                

                df=get_data(result)
                st.dataframe(df)

                if st.button("Upload to Database"):
                        insert_data()

                if st.button("View Data"):
                        show_data()
                
#====================================================page 2====================================================================================


#editing the table
if selected == "Modify":
        # Connect to MYSQL and fetch data
        data_dict, column_names = fetch_data()

        # Create a dropdown box and populate it with the card holders
        selected_option = st.selectbox("Select a card holder:", ["None"] + list(data_dict.keys()))

        tab1, tab2 = st.tabs(["Edit The Data", "Delete The Data"])

        with tab1:
        # Display text boxes for each column of the selected card holder
                if selected_option != "None":
                        st.write("You selected:", selected_option)
                        if selected_option in data_dict:
                                st.write("Modify the data:")
                                updated_values = list(data_dict[selected_option])  # Create a list of the original values
                                for i, column_name in enumerate(column_names):
                                        new_value = st.text_input(column_name, data_dict[selected_option][i])
                                        updated_values[i] = new_value  # Update the corresponding value
                                        st.write(f"Updated {column_name}: {new_value}")

                                # Add a button to save the updated data
                                if st.button("Update"):
                                        update_data(selected_option, updated_values, column_names)
                                        st.success("Data has been updated.")

                        else:
                                st.write("Option not found in data.")
                else:
                        st.write("No card holder selected.")

                #viewing the updated data
                if st.button("View Data"):
                        show_data()

        with tab2:
                if selected_option != "None":
                        st.write("You selected:", selected_option)
                        if selected_option in data_dict:
                                query = 'SELECT * FROM card_details WHERE card_holder = %s'
                                mycursor.execute(query, (selected_option,))
                                df = mycursor.fetchall()
                                st.write(pd.DataFrame(df, columns=['Card Holder','Copany Name', 'Designation','Mobile Number', 'Email', 
                                                                      'Website', 'Area', 'City','State', 'Pin Code']))
                                st.write("The Data Of This Card Holder Will Be Deleted")
                                if st.button("Delete"):
                                        delete_data()
                                        st.success("Data Successfully deleted!!")
                if st.button("View"):
                                show_data()