namespace JoyGame
{
    /// <summary>
    /// 确定性随机：xorshift32。四个示例（cpp / csharp / lua / js）共用同一算法与
    /// 同一套种子，冒烟输出的行为指纹才能横向比对。
    ///
    /// 不用 System.Random：它的算法在 Lua / JS / C++ 里没有逐位等价的实现，
    /// 换语言就会得到不同的敌人速度，指纹对不上。
    /// </summary>
    internal sealed class Rng
    {
        private uint _state;

        public Rng(uint seed)
        {
            _state = seed == 0u ? 1u : seed;
        }

        public uint NextU32()
        {
            _state ^= _state << 13;
            _state ^= _state >> 17;
            _state ^= _state << 5;
            return _state;
        }

        /// <summary>[0,1)：取高 24 位，四种语言都能逐位复现。</summary>
        public double NextDouble()
        {
            return (NextU32() >> 8) * (1.0 / 16777216.0);
        }

        public int Next(int maxExclusive)
        {
            return (int)(NextU32() % (uint)maxExclusive);
        }
    }
}
