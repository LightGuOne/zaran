-- author: https://github.com/ChaosAlphard
-- 说明 https://github.com/gaboolic/rime-shuangpin-fuzhuma/pull/41
local M = {}

function M.init(env)
  local config = env.engine.schema.config
  env.name_space = env.name_space:gsub('^*', '')
  M.prefix = 'V'
end

local function startsWith(str, start)
  return string.sub(str, 1, string.len(start)) == start
end

local function truncateFromStart(str, truncateStr)
  return string.sub(str, string.len(truncateStr) + 1)
end

-- 添加的日期输出函数
local function yield_cand(seg, input, text, comment)
    local cand = Candidate('', seg.start, seg._end, text, comment)
    cand.quality = 10000
    yield(cand)
end

-------------------------------------------------------------
---- 简单计算器部分
-------------------------------------------------------------

-- 函数表
local calcPlugin = {
    -- e, exp(1) = e^1 = e
    e = math.exp(1),
    -- π
    pi = math.pi,
  -- 随机数
  rdm = function(...) return math.random(...) end,
  -- 三角函数
  sin = math.sin, cos = math.cos, tan = math.tan,
  asin = math.asin, acos = math.acos, atan = math.atan,
  sinh = math.sinh, cosh = math.cosh, tanh = math.tanh,
  atan2 = math.atan2,
  -- 角度转换
  deg = math.deg, rad = math.rad,
  -- 指数和对数
  exp = math.exp, sqrt = math.sqrt, ldexp = math.ldexp,
  log = function(x, y) return (x > 0 and y > 0) and math.log(y) / math.log(x) or nil end,
  loge = function(x) return x > 0 and math.log(x) or nil end,
  log10 = function(x) return x > 0 and math.log10(x) or nil end,
  -- 统计函数
  avg = function(...) local n = select("#", ...); if n == 0 then return nil end; local sum = 0; for i = 1, n do sum = sum + select(i, ...) end; return sum / n end,
  var = function(...) local n = select("#", ...); if n == 0 then return nil end; local sum, sum_sq = 0, 0; for i = 1, n do local v = select(i, ...); sum = sum + v; sum_sq = sum_sq + v * v end; return (sum_sq - sum * sum / n) / n end,
  -- 阶乘
  fact = function(x) if x < 0 then return nil elseif x <= 1 then return 1 else local r = 1; for i = 2, x do r = r * i end; return r end end
}

-- 阶乘符号替换函数（保持原样，因为它已经是单行）
local function replaceToFactorial(str) return str:gsub("([0-9]+)!", "fact(%1)") end

-------------------------------------------------------------
--大写金额部分
-------------------------------------------------------------


local function splitNumPart(str)
  local part = {}
  part.int, part.dot, part.dec = string.match(str, "^(%d*)(%.?)(%d*)")
  return part
end

local function GetPreciseDecimal(nNum, n)
  if type(nNum) ~= "number" then nNum = tonumber(nNum) end
  n = n or 0;
  n = math.floor(n)
  if n < 0 then n = 0 end
  local nDecimal = 10 ^ n
  local nTemp = math.floor(nNum * nDecimal);
  local nRet = nTemp / nDecimal;
  return nRet;
end

local function decimal_func(str, posMap, valMap)
  local dec
  posMap = posMap or { [1] = "角", [2] = "分", [3] = "厘", [4] = "毫" }
  valMap = valMap or { [0] = "零", "壹", "贰", "叁", "肆", "伍", "陆", "柒", "捌", "玖" }
  if #str > 4 then dec = string.sub(tostring(str), 1, 4) else dec = tostring(str) end
  dec = string.gsub(dec, "0+$", "")

  if dec == "" then return "整" end

  local result = ""
  for pos = 1, #dec do
      local val = tonumber(string.sub(dec, pos, pos))
      if val ~= 0 then result = result .. valMap[val] .. posMap[pos] else result = result .. valMap[val] end
  end
  result = result:gsub(valMap[0] .. valMap[0], valMap[0])
  return result:gsub(valMap[0] .. valMap[0], valMap[0])
end

-- 把数字串按千分位四位数分割，进行转换为中文
local function formatNum(num, t)
  local digitUnit, wordFigure
  local result = ""
  num = tostring(num)
  if tonumber(t) < 1 then digitUnit = { "", "十", "百", "千" } else digitUnit = { "", "拾", "佰", "仟" } end
  if tonumber(t) < 1 then
      wordFigure = { "〇", "一", "二", "三", "四", "五", "六", "七", "八", "九" }
  else
      wordFigure = { "零", "壹", "贰", "叁", "肆", "伍", "陆", "柒", "捌", "玖" }
  end
  if string.len(num) > 4 or tonumber(num) == 0 then return wordFigure[1] end
  local lens = string.len(num)
  for i = 1, lens do
      local n = wordFigure[tonumber(string.sub(num, -i, -i)) + 1]
      if n ~= wordFigure[1] then result = n .. digitUnit[i] .. result else result = n .. result end
  end
  result = result:gsub(wordFigure[1] .. wordFigure[1], wordFigure[1])
  result = result:gsub(wordFigure[1] .. "$", "")
  result = result:gsub(wordFigure[1] .. "$", "")

  return result
end

-- 数值转换为中文
local function number2cnChar(num, flag, digitUnit, wordFigure) --flag=0中文小写反之为大写
  local result = ""

  if tonumber(flag) < 1 then
      digitUnit = digitUnit or { [1] = "万", [2] = "亿" }
      wordFigure = wordFigure or { [1] = "〇", [2] = "一", [3] = "十", [4] = "元" }
  else
      digitUnit = digitUnit or { [1] = "万", [2] = "亿" }
      wordFigure = wordFigure or { [1] = "零", [2] = "壹", [3] = "拾", [4] = "元" }
  end
  local lens = string.len(num)
  if lens < 5 then
      result = formatNum(num, flag)
  elseif lens < 9 then
      result = formatNum(string.sub(num, 1, -5), flag) .. digitUnit[1] .. formatNum(string.sub(num, -4, -1), flag)
  elseif lens < 13 then
      result = formatNum(string.sub(num, 1, -9), flag) ..
          digitUnit[2] ..
          formatNum(string.sub(num, -8, -5), flag) .. digitUnit[1] .. formatNum(string.sub(num, -4, -1), flag)
  else
      result = ""
  end

  result = result:gsub("^" .. wordFigure[1], "")
  result = result:gsub(wordFigure[1] .. digitUnit[1], "")
  result = result:gsub(wordFigure[1] .. digitUnit[2], "")
  result = result:gsub(wordFigure[1] .. wordFigure[1], wordFigure[1])
  result = result:gsub(wordFigure[1] .. "$", "")
  if lens > 4 then result = result:gsub("^" .. wordFigure[2] .. wordFigure[3], wordFigure[3]) end
  if result ~= "" then result = result .. wordFigure[4] else result = "数值超限！" end

  return result
end

local function number2zh(num, t)
  local result, wordFigure
  result = ""
  if tonumber(t) < 1 then
      wordFigure = { "〇", "一", "二", "三", "四", "五", "六", "七", "八", "九" }
  else
      wordFigure = { "零", "壹", "贰", "叁", "肆", "伍", "陆", "柒", "捌", "玖" }
  end
  if tostring(num) == nil then return "" end
  for pos = 1, string.len(num) do
      result = result .. wordFigure[tonumber(string.sub(num, pos, pos) + 1)]
  end
  result = result:gsub(wordFigure[1] .. wordFigure[1], wordFigure[1])
  return result:gsub(wordFigure[1] .. wordFigure[1], wordFigure[1])
end

local function number_translatorFunc(num)
  local numberPart = splitNumPart(num)
  local result = {}
  if numberPart.dot ~= "" then
      table.insert(result,
          { number2cnChar(numberPart.int, 0, { "万", "亿" }, { "〇", "一", "十", "点" }) .. number2zh(numberPart.dec, 0),
              "〔数字小写〕" })
      table.insert(result,
          { number2cnChar(numberPart.int, 1, { "萬", "億" }, { "〇", "一", "十", "点" }):gsub("^拾", "壹拾") .. number2zh(numberPart.dec, 1),
              "〔数字大写〕" })
  else
      table.insert(result, { number2cnChar(numberPart.int, 0, { "万", "亿" }, { "〇", "一", "十", "" }), "〔数字小写〕" })
      table.insert(result, { number2cnChar(numberPart.int, 1, { "萬", "億" }, { "零", "壹", "拾", "" }):gsub("^拾", "壹拾"), "〔数字大写〕" })
  end
  table.insert(result,
      { number2cnChar(numberPart.int, 0) ..
      decimal_func(numberPart.dec, { [1] = "角", [2] = "分", [3] = "厘", [4] = "毫" },
          { [0] = "〇", "一", "二", "三", "四", "五", "六", "七", "八", "九" }), "〔金额小写〕" })

  local number2cnCharInt = number2cnChar(numberPart.int, 1)
  local number2cnCharDec = decimal_func(numberPart.dec, { [1] = "角", [2] = "分", [3] = "厘", [4] = "毫" }, { [0] = "零", "壹", "贰", "叁", "肆", "伍", "陆", "柒", "捌", "玖" })
  if string.len(numberPart.int) > 4 and number2cnCharInt:find('^拾[壹贰叁肆伍陆柒捌玖]?') and number2cnCharInt:find('[万亿]')  then -- 简易地规避 utf8 匹配问题
      local number2cnCharInt_var = number2cnCharInt:gsub('^拾', '壹拾')
      table.insert(result, { number2cnCharInt_var .. number2cnCharDec , "〔金额大写〕"})
      -- 会计书写要求 https://github.com/iDvel/rime-ice/issues/989
  else
      table.insert(result, { number2cnCharInt .. number2cnCharDec , "〔金额大写〕"})
  end
  local result = {result[1], result[4], result[3]}
  return result
end







-------------------------------------------------------------
--引导部分
-------------------------------------------------------------



function M.func(input, seg, env)
  if not startsWith(input, M.prefix) then return end
  -- 提取算式
  local express = truncateFromStart(input, M.prefix)    --移除前缀
  
  -- 新增：只输入V时输出日期
  if express == "" then
      local current_time = os.time()
      yield_cand(seg, input, os.date('%Y/%m/%d', current_time), "")
      yield_cand(seg, input, os.date('%Y%m%d', current_time), "")
      yield_cand(seg, input, string.format('%d', current_time), "")
      return
  end
  
  -- 算式长度 < 2 直接终止(没有计算意义)
  if (string.len(express) < 2) then return end

  local part_int, part_dot, part_dec = string.match(express, "^(%d*)(%.?)(%d*)$")
  if not part_int or not part_dot or not part_dec then
    local code = replaceToFactorial(express)   --将阶乘符号换成lua的格式 
    local success, result = pcall(load("return " .. code, "calculate", "t", calcPlugin))
    if success then   -- 如果有计算结果
      yield(Candidate(input, seg.start, seg._end, result, ""))
      yield(Candidate(input, seg.start, seg._end, express .. "=" .. result, ""))
      numberPart = number_translatorFunc(result)
      
      if not string.find(numberPart[1][1], "数值超限！") then
        numberPartone=numberPart[1][1]:gsub('点〇$', '')
        yield(Candidate(input, seg.start, seg._end, numberPartone, ""))
      end
    else
      yield(Candidate(input, seg.start, seg._end, express, "解析失败"))
    end
  else
    numberPart = number_translatorFunc(express)
    if express and #express > 0 and #numberPart > 0 then
        for i = 1, #numberPart do
            yield(Candidate(input, seg.start, seg._end, numberPart[i][1], numberPart[i][2]))
        end
    end
  end
end

return M
