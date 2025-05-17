from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackQueryHandler
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

TOKEN = '7512886647:AAHmNPHtSEnGvcfKNmzS7Gen0iLPyOYIJVk'  # Replace with your bot token
user_data_store = {}

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! 👋\nPlease upload a CSV file for analysis.")

# Handle CSV uploads
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document

    if not document.file_name.endswith(".csv"):
        await update.message.reply_text("⚠️ Please upload a valid .csv file.")
        return

    await update.message.reply_text("📥 Analyzing your file... Please wait ⏳")

    file = await document.get_file()
    file_path = f"data_{update.message.chat_id}.csv"
    await file.download_to_drive(file_path)

    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        await update.message.reply_text(f"❌ Error reading CSV: {str(e)}")
        os.remove(file_path)
        return

    row_count, col_count = df.shape
    await update.message.reply_text(f"✅ File received. Rows: {row_count}, Columns: {col_count}")

    # Store dataframe for user
    user_data_store[update.message.chat_id] = df

    # Suggest best plots
    suggestions = get_plot_suggestions(df)

    buttons = [
        [InlineKeyboardButton(f"{label} ({acc}%)", callback_data=plot)]
        for plot, label, acc in suggestions
    ]

    await update.message.reply_text(
        "📊 Based on your data, here are the best visualization suggestions:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

    os.remove(file_path)

# Suggest graphs based on simple logic

def get_plot_suggestions(df):
    numeric_cols = df.select_dtypes(include='number')
    suggestions = []
    if numeric_cols.shape[1] >= 2:
        suggestions.append(('heatmap', 'Heatmap', 95))
        suggestions.append(('pairplot', 'Pairplot', 90))
    if numeric_cols.shape[0] > 10:
        suggestions.append(('lineplot', 'Line Plot', 88))
        suggestions.append(('barplot', 'Bar Plot', 85))
    suggestions.append(('histplot', 'Histogram', 80))
    return suggestions[:5]

# Handle button selection
async def handle_plot_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chart_type = query.data

    df = user_data_store.get(query.message.chat_id)
    if df is None:
        await query.edit_message_text("❌ No data found. Please upload the CSV again.")
        return

    try:
        plt.figure(figsize=(10, 6))
        numeric_cols = df.select_dtypes(include='number')

        if chart_type == 'heatmap':
            sns.heatmap(numeric_cols.corr(), annot=True, cmap='coolwarm')
        elif chart_type == 'pairplot':
            sns.pairplot(numeric_cols)
        elif chart_type == 'lineplot':
            numeric_cols.plot()
        elif chart_type == 'barplot':
            numeric_cols.mean().plot(kind='bar')
        elif chart_type == 'histplot':
            numeric_cols.hist(figsize=(10, 6))

        plot_path = f"plot_{query.message.chat_id}.png"
        plt.tight_layout()
        plt.savefig(plot_path)
        plt.close()

        await context.bot.send_photo(chat_id=query.message.chat_id, photo=open(plot_path, 'rb'))
        os.remove(plot_path)

    except Exception as e:
        await query.edit_message_text(f"❌ Error creating plot: {str(e)}")
        return

    await query.edit_message_text(f"✅ Here's your {chart_type.capitalize()} 📈")

# Set up the bot
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
app.add_handler(CallbackQueryHandler(handle_plot_choice))

app.run_polling()